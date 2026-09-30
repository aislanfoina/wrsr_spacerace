// experts.cpp - a fourth education tier, earned by time in a training building.
//
// Education is one float per citizen at person+0xA8 (Person.fEducation in the
// scripting VM): [0,1) none, [1,2) basic, [2,3) higher. Nothing in the game
// caps it at 3, and every reader tests >= 1 / >= 2, so [3,4) is a valid tier
// the base game already treats as higher education - and it is saved with the
// citizen as it is. This plugin is the only thing that puts citizens there:
//
//   A training building runs a class of up to class_size citizens. A citizen
//   who works a shift there and meets its gates (education, age at
//   person+0xD4, health at person+0xE0) joins the class if a seat is free,
//   best-educated first, and stays in it whatever job they take next: the
//   game hands out jobs day by day (a Star City shift changed hands completely
//   within three days in a test), so time counted per person at the building
//   would never add up. Every game day each member gains rate x the share of
//   the class that the building's eligible staff fill that day (a full house
//   = one tier in days_per_tier days). Members leave at max_education, or
//   when they fail a gate or leave the republic. Crossing 3.0 makes an expert.
//   The class lives in memory; after a reload it refills, and partly trained
//   citizens return to it first because seats go to the best-educated.
//
//   Person pointers, checked in a running game (build/memprobe.py, 2026-09-29):
//   +0x80 workplace (206 at a MIK with 175 workers + 27 engineers), +0x40 the
//   building the citizen is in right now (shops, school, work - never home),
//   +0x58 the customs house the citizen immigrated through.
//
// Everything is configured in experts.ini beside the DLL, one [building:<object>]
// section per training building, matched against the object part of the type
// ident ("9000101/sr_training" matches [building:sr_training]). Other mods add
// their own sections; nothing here knows about space.
//
// Hook: a post-hook on TickAllBuildings (SOVIET64 0x139A70), chained after any
// plugin already there. The world date is read from game+0x590 (day of year)
// and game+0x594 (year).

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

static const TsmHost* H;

#define RVA_TICK_ALL   0x139A70
#define CTX_PERSONS    0x126A8
#define CTX_DAY        0x590
#define CTX_YEAR       0x594
#define PER_WORKPLACE  0x80
#define PER_EDUCATION  0xA8
#define PER_AGE        0xD4
#define PER_HEALTH     0xE0
#define BLD_TYPEDESC   0x318

static const unsigned char kTickPro[19] = { 0x48, 0x8B, 0xC4, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57,
                                            0x48, 0x8D, 0xA8, 0x78, 0xFA, 0xFF, 0xFF };

typedef void (*TickAllFn)(void* ctx);
static TickAllFn g_origTick;

#define MAX_CLASS 256

struct Rule
{
    char  object[64];
    float rate;          // education per game day for a class member, with a full house
    float minEdu, maxEdu;
    float minAge, maxAge;
    float minHealth;
    int   classSize;
    unsigned char* member[MAX_CLASS];   // the class: citizen pointers
    int   nmember;
    int   joined, graduated, dropped;  // this session
};
#define MAX_RULES 16
static Rule g_rules[MAX_RULES];
static int  g_nrules;
static int  g_refreshTicks = 60;

// per rule, for the log: who works there today and which gate stopped them
struct Census { int employed, lowEdu, topped, age, health, eligible; float ageMin, ageMax, eduMax, classMax; };
static Census g_census[MAX_RULES];

static unsigned g_ticks, g_lastRun;
static int      g_lastDay = -1, g_lastYear = -1;
static ULONGLONG g_logAt;
static int      g_experts, g_training, g_promoted;
static char     g_iniPath[MAX_PATH];

static void LogLine(const char* fmt, ...)
{
    char buf[512];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    H->log("%s", buf);
}

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

static int LooksLikePointer(const void* p)
{
    ULONG_PTR v = (ULONG_PTR)p;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull || (v & 7)) return 0;
    return H->readablePtr(p, 16);
}

// the object part of a building's type ident, or NULL
static const char* BuildingObject(unsigned char* b)
{
    if (!Readable(b + BLD_TYPEDESC, 8)) return NULL;
    unsigned char* td = *(unsigned char**)(b + BLD_TYPEDESC);
    if (!LooksLikePointer(td) || !Readable(td, 0x40)) return NULL;
    const char* s = (const char*)td;
    int i = 0;
    for (; i < 0x40; ++i)
    {
        if (s[i] == 0) break;
        if (s[i] < 0x20 || s[i] > 0x7E) return NULL;
    }
    if (i < 2 || i >= 0x40) return NULL;
    const char* slash = strrchr(s, '/');
    return slash ? slash + 1 : s;
}

static const Rule* RuleFor(unsigned char* b)
{
    const char* obj = BuildingObject(b);
    if (!obj) return NULL;
    for (int i = 0; i < g_nrules; ++i)
        if (_stricmp(obj, g_rules[i].object) == 0) return &g_rules[i];
    return NULL;
}

// days elapsed since the last run, from the world's own calendar (0 on the first call or a date jump backwards)
static int DaysElapsed(unsigned char* ctx)
{
    if (!Readable(ctx + CTX_DAY, 8)) return 0;
    int day = *(int*)(ctx + CTX_DAY), year = *(int*)(ctx + CTX_YEAR);
    if (day < 0 || day > 366 || year < 1800 || year > 3000) return 0;
    int d = 0;
    if (g_lastYear >= 0)
    {
        d = (year - g_lastYear) * 365 + (day - g_lastDay);
        if (d < 0 || d > 3650) d = 0;       // a different world was loaded
    }
    g_lastDay = day; g_lastYear = year;
    return d;
}

// gates a class member must keep meeting (education below the cap, age, health)
static int Fit(const Rule* r, unsigned char* p)
{
    float edu = *(float*)(p + PER_EDUCATION), age = *(float*)(p + PER_AGE), hp = *(float*)(p + PER_HEALTH);
    return edu >= r->minEdu && edu < r->maxEdu && age >= r->minAge && age <= r->maxAge && hp >= r->minHealth;
}

static int InClass(const Rule* r, const unsigned char* p)
{
    for (int k = 0; k < r->nmember; ++k)
        if (r->member[k] == p) return 1;
    return 0;
}

// one class per citizen: a graduate who passes two buildings' gates (Star City and OKB-1 overlap
// at ages 30-35) would otherwise train in both at once
static int InAnyClass(const unsigned char* p)
{
    for (int r = 0; r < g_nrules; ++r)
        if (InClass(&g_rules[r], p)) return 1;
    return 0;
}

#define MAX_CANDIDATES 512
struct Candidate { unsigned char* p; float edu; };

static int ByEducationDesc(const void* a, const void* b)
{
    float x = ((const Candidate*)a)->edu, y = ((const Candidate*)b)->edu;
    return x < y ? 1 : x > y ? -1 : 0;
}

static void Train(unsigned char* ctx, int days)
{
    if (!Readable(ctx + CTX_PERSONS, 16)) return;
    unsigned char** begin = *(unsigned char***)(ctx + CTX_PERSONS);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_PERSONS + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    if (n > 200000) return;
    int experts = 0;
    static unsigned char seen[MAX_RULES][MAX_CLASS];
    static Candidate cand[MAX_RULES][MAX_CANDIDATES];
    int ncand[MAX_RULES] = { 0 };
    memset(seen, 0, sizeof seen);
    memset(g_census, 0, sizeof g_census);
    for (int r = 0; r < g_nrules; ++r) { g_census[r].ageMin = 999.0f; g_census[r].ageMax = -1.0f; g_census[r].eduMax = -1.0f; g_census[r].classMax = -1.0f; }

    // one pass: count experts, mark class members still in the republic, census today's staff, collect newcomers
    for (SIZE_T i = 0; i < n; ++i)
    {
        if (!Readable(begin + i, 8)) break;
        unsigned char* p = begin[i];
        if (!LooksLikePointer(p) || !Readable(p + PER_EDUCATION, 4) || !Readable(p + PER_HEALTH, 4)) continue;
        float edu = *(float*)(p + PER_EDUCATION);
        if (!(edu >= 0.0f && edu < 4.0f)) continue;             // NaN or not a citizen record
        if (edu >= 3.0f) ++experts;
        for (int r = 0; r < g_nrules; ++r)
            for (int k = 0; k < g_rules[r].nmember; ++k)
                if (g_rules[r].member[k] == p) seen[r][k] = 1;
        if (!Readable(p + PER_WORKPLACE, 8)) continue;
        unsigned char* b = *(unsigned char**)(p + PER_WORKPLACE);
        if (!LooksLikePointer(b)) continue;
        const Rule* r = RuleFor(b);
        if (!r) continue;
        int ri = (int)(r - g_rules);
        Census* c = &g_census[ri];
        float age = *(float*)(p + PER_AGE), hp = *(float*)(p + PER_HEALTH);
        ++c->employed;
        if (age < c->ageMin) c->ageMin = age;
        if (age > c->ageMax) c->ageMax = age;
        if (edu > c->eduMax) c->eduMax = edu;
        if (edu < r->minEdu) { ++c->lowEdu; continue; }
        if (edu >= r->maxEdu) { ++c->topped; continue; }
        if (age < r->minAge || age > r->maxAge) { ++c->age; continue; }
        if (hp < r->minHealth) { ++c->health; continue; }
        ++c->eligible;
        if (ncand[ri] < MAX_CANDIDATES && !InAnyClass(p)) { cand[ri][ncand[ri]].p = p; cand[ri][ncand[ri]].edu = edu; ++ncand[ri]; }
    }

    for (int ri = 0; ri < g_nrules; ++ri)
    {
        Rule* r = &g_rules[ri];
        // members who left the republic, graduated or failed a gate give up their seat
        int keep = 0;
        for (int k = 0; k < r->nmember; ++k)
        {
            unsigned char* p = r->member[k];
            if (!seen[ri][k]) { ++r->dropped; continue; }
            if (*(float*)(p + PER_EDUCATION) >= r->maxEdu) { ++r->graduated; continue; }
            if (!Fit(r, p)) { ++r->dropped; continue; }
            r->member[keep++] = p;
        }
        r->nmember = keep;
        // free seats go to today's eligible staff, best-educated first
        if (ncand[ri] > 1) qsort(cand[ri], ncand[ri], sizeof(Candidate), ByEducationDesc);
        for (int k = 0; k < ncand[ri] && r->nmember < r->classSize; ++k)
        {
            r->member[r->nmember++] = cand[ri][k].p;
            ++r->joined;
        }
        // a day of lessons: the whole class moves by rate x (eligible staff today / class size)
        if (days > 0 && r->nmember > 0)
        {
            float fill = (float)g_census[ri].eligible / (float)r->classSize;
            if (fill > 1.0f) fill = 1.0f;
            float gain = r->rate * days * fill;
            for (int k = 0; k < r->nmember; ++k)
            {
                float* edu = (float*)(r->member[k] + PER_EDUCATION);
                float before = *edu;
                *edu += gain;
                if (*edu > r->maxEdu) *edu = r->maxEdu;
                if (before < 3.0f && *edu >= 3.0f) ++g_promoted;
            }
        }
        for (int k = 0; k < r->nmember; ++k)
        {
            float e = *(float*)(r->member[k] + PER_EDUCATION);
            if (e > g_census[ri].classMax) g_census[ri].classMax = e;
        }
    }
    g_experts = experts;
    g_training = 0;
    for (int ri = 0; ri < g_nrules; ++ri) g_training += g_rules[ri].nmember;
}

static void DetourTickAll(void* ctx)
{
    g_origTick(ctx);
    ++g_ticks;
    if ((int)(g_ticks - g_lastRun) < g_refreshTicks) return;
    g_lastRun = g_ticks;
    __try
    {
        int days = DaysElapsed((unsigned char*)ctx);
        Train((unsigned char*)ctx, days);
        ULONGLONG t = GetTickCount64();
        if (t - g_logAt > 60000)
        {
            g_logAt = t;
            LogLine("experts  %d experts in the republic, %d citizens in training classes, %d promoted this session", g_experts, g_training, g_promoted);
            for (int r = 0; r < g_nrules; ++r)
            {
                const Census* c = &g_census[r];
                const Rule* R = &g_rules[r];
                if (!c->employed && !R->nmember) continue;
                LogLine("experts    %s: class %d/%d (best %.2f; %d joined, %d graduated, %d dropped this session) - today %d employed, %d eligible; %d below education %.1f, %d at the cap, %d outside age %.0f-%.0f, %d under health %.2f",
                        R->object, R->nmember, R->classSize, c->classMax, R->joined, R->graduated, R->dropped, c->employed, c->eligible,
                        c->lowEdu, R->minEdu, c->topped, c->age, R->minAge, R->maxAge, c->health, R->minHealth);
            }
        }
    }
    __except (H->faultFilter("experts", GetExceptionInformation())) {}
}

// ----------------------------------------------------------------- config ----

static void Trim(char* s)
{
    char* e = s + strlen(s);
    while (e > s && (e[-1] == ' ' || e[-1] == '\t' || e[-1] == '\r' || e[-1] == '\n')) *--e = 0;
    char* b = s;
    while (*b == ' ' || *b == '\t') ++b;
    if (b != s) memmove(s, b, strlen(b) + 1);
}

static void LoadConfig(void)
{
    HMODULE self = NULL;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCSTR)&LoadConfig, &self) && GetModuleFileNameA(self, g_iniPath, MAX_PATH))
    {
        char* slash = strrchr(g_iniPath, '\\');
        if (slash) strcpy_s(slash + 1, MAX_PATH - (slash + 1 - g_iniPath), "experts.ini");
    }
    FILE* f = NULL;
    if (!g_iniPath[0] || fopen_s(&f, g_iniPath, "r") != 0 || !f)
    {
        LogLine("experts  no experts.ini next to the DLL (%s) - no training buildings", g_iniPath);
        return;
    }
    char line[256];
    Rule* cur = NULL;
    while (fgets(line, sizeof line, f))
    {
        char* semi = strchr(line, ';'); if (semi) *semi = 0;
        Trim(line);
        if (!line[0]) continue;
        if (line[0] == '[')
        {
            cur = NULL;
            char* rb = strchr(line, ']'); if (rb) *rb = 0;
            if (_strnicmp(line + 1, "building:", 9) == 0 && g_nrules < MAX_RULES)
            {
                cur = &g_rules[g_nrules++];
                memset(cur, 0, sizeof *cur);
                strncpy_s(cur->object, sizeof cur->object, line + 10, _TRUNCATE);
                Trim(cur->object);
                cur->rate = 1.0f / 365.0f; cur->minEdu = 2.0f; cur->maxEdu = 3.99f;
                cur->minAge = 0.0f; cur->maxAge = 200.0f; cur->minHealth = 0.0f;
                cur->classSize = 40;
            }
            continue;
        }
        char* eq = strchr(line, '='); if (!eq) continue;
        *eq = 0; char* key = line; char* val = eq + 1;
        Trim(key); Trim(val);
        float v = (float)atof(val);
        if (!cur)
        {
            if (_stricmp(key, "refresh_ticks") == 0 && v >= 1.0f) g_refreshTicks = (int)v;
            continue;
        }
        if      (_stricmp(key, "rate_per_day") == 0)  cur->rate = v;
        else if (_stricmp(key, "days_per_tier") == 0 && v > 0.0f) cur->rate = 1.0f / v;
        else if (_stricmp(key, "min_education") == 0) cur->minEdu = v;
        else if (_stricmp(key, "max_education") == 0) cur->maxEdu = (v > 3.99f ? 3.99f : v);
        else if (_stricmp(key, "min_age") == 0)       cur->minAge = v;
        else if (_stricmp(key, "max_age") == 0)       cur->maxAge = v;
        else if (_stricmp(key, "min_health") == 0)    cur->minHealth = v;
        else if (_stricmp(key, "class_size") == 0)    cur->classSize = (v < 1.0f ? 1 : v > MAX_CLASS ? MAX_CLASS : (int)v);
    }
    fclose(f);
    for (int i = 0; i < g_nrules; ++i)
        LogLine("experts  training building '%s': class of %d, %.4f education/day with a full house (%.0f days per tier), education %.2f-%.2f, age %.0f-%.0f, health >= %.2f",
                g_rules[i].object, g_rules[i].classSize, g_rules[i].rate, g_rules[i].rate > 0 ? 1.0f / g_rules[i].rate : 0.0f,
                g_rules[i].minEdu, g_rules[i].maxEdu, g_rules[i].minAge, g_rules[i].maxAge, g_rules[i].minHealth);
}

// --------------------------------------------------------------- exports ----

static const unsigned char* LiveOrPristine(const unsigned char* target, const unsigned char* pristine, size_t len, unsigned char* buf, const char* label)
{
    if (!H->readablePtr(target, len)) return pristine;
    if (memcmp(target, pristine, len) == 0) return pristine;
    memcpy(buf, target, len);
    LogLine("%s: target already patched by another plugin, chaining onto the live bytes", label);
    return buf;
}

extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void) { return TSM_API_VERSION; }

extern "C" __declspec(dllexport) int TsmPluginInit(const TsmHost* host, TsmPluginInfo* info)
{
    H = host;
    info->name    = "experts";
    info->version = "0.1";
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    LoadConfig();
    unsigned char live[19];
    const unsigned char* expect = LiveOrPristine(H->exeBase + RVA_TICK_ALL, kTickPro, 19, live, "experts TickAllBuildings");
    if (!H->installInlineHook(H->exeBase + RVA_TICK_ALL, (void*)&DetourTickAll, (void**)&g_origTick, expect, 19, "experts TickAllBuildings"))
    {
        LogLine("experts  hook TickAllBuildings at 0x%X did not match - not installed", RVA_TICK_ALL);
        return 1;
    }
    LogLine("experts  active: %d training building(s); education [3,4) is the expert tier", g_nrules);
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
