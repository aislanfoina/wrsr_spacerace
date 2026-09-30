// spacerace.cpp - the Space Race in any game: research branch, names, programme.
//
// Four small jobs, all at start-up except the last:
//
//   1. Install data. spacerace_data\research\*.png go to media_soviet\research
//      (research icons are looked up there by name), and the programme scenario
//      spacerace_data\scenarios\spacerace to media_soviet\scenarios\spacerace.
//      Only our own files are written; nothing of the game's is touched.
//
//   2. Research branch. SOVIET64 reads research\research.ini with fopen after
//      C3DPath_GetFullPath (0x2F3D12). A merged copy - the vanilla file, plus an
//      $UNLOCK_RESEARCH line in the vanilla parents named by inject.ini, plus our
//      research_space.ini with {KIT} replaced by the building kit's item id - is
//      written beside the DLL, and SOVIET64's fopen import is swapped so that one
//      path opens the merged file. Every other fopen passes straight through.
//
//   3. Names. Research names and descriptions are language ids. Ours start at
//      591000 (the game's highest is 580231); SOVIET64's import of
//      C3D_LANGUAGE::GetString is swapped and answers those ids from
//      spacerace_data\strings.txt, passing every other id through.
//
//   4. The programme. On every world load the game parses stats.ini (setting the
//      scenario/mission std::strings at 0x9E8648 / 0x9E8668 and the auto-start
//      flag at 0x9E8688 for $ScenarioAutoStart) and then enumerates scenarios
//      (0x5CB7C0, one caller). A hook there sees an empty scenario - an ordinary
//      game - and sets spacerace/programme with the auto-start flag, exactly what
//      a map's "$ScenarioAutoStart spacerace programme" would do. Campaigns,
//      tutorials, Year Zero and saves already running a scenario are left alone.
//      The programme sleeps until the space research starts.
//
//   5. Pads to the MIK. The MIK is an aircraft production line; a finished
//      aircraft goes to a free station of a building linked to the line
//      (0x1CA97D), and the rocket list only opens once one is linked. A link is
//      the child's parent pointer (building+0x5B0) plus the parent's child list
//      (+0x5B8, added by 0x3BB8F0(game, parent, child), as the game does when it
//      creates or loads a linked building; saves keep it). The game's own way to
//      make one at placement did not take for our pads, so a post-hook on
//      TickAllBuildings links every unlinked launch pad (object sr_pad_*) to the
//      nearest MIK (object sr_mik) within link_range metres.

#include "../../../vendor/TesmioLoader/src/tesmio_api.h"

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>
#include <wchar.h>
#include <math.h>

static const TsmHost* H;

#define RVA_SCEN_ENUM      0x5CB7C0
#define RVA_STR_ASSIGN     0x8EB20
#define RVA_SCEN_NAME      0x9E8648
#define RVA_SCEN_MISSION   0x9E8668
#define RVA_SCEN_AUTOSTART 0x9E8688
#define STRING_ID_MIN      591000
#define STRING_ID_MAX      591999

static const unsigned char kEnumPro[18] = { 0x40, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57,
                                            0x48, 0x8D, 0xAC, 0x24, 0x90, 0xDE, 0xFF, 0xFF };

#define RVA_TICK_ALL       0x139A70
#define RVA_ADD_CHILD      0x3BB8F0
#define CTX_BUILDINGS      0x11B08
#define BLD_TYPEDESC       0x318
#define BLD_NODE           0x320
#define BLD_PARENT         0x5B0
#define TD_TYPE            0x360
#define TYPE_PRODUCTION    0x28
#define TYPE_AIR_PARKING   0x2F

static const unsigned char kTickPro[19] = { 0x48, 0x8B, 0xC4, 0x55, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56, 0x41, 0x57,
                                            0x48, 0x8D, 0xA8, 0x78, 0xFA, 0xFF, 0xFF };

typedef void (*TickAllFn)(void* ctx);
typedef void (*AddChildFn)(void* ctx, void* parent, void* child);
typedef float* (*GetPositionFn)(void* node, float* out);

typedef FILE* (__cdecl* FopenFn)(const char* path, const char* mode);
typedef wchar_t* (*GetStringFn)(void* self, int id);
typedef void* (*EnumFn)(void* a, void* b, void* c, void* d);
typedef void* (*StrAssignFn)(void* self, const char* s, size_t n);

static FopenFn     g_origFopen;
static GetStringFn g_origGetString;
static EnumFn      g_origEnum;
static TickAllFn   g_origTick;
static GetPositionFn g_getPos;
static unsigned    g_ticks;
static float       g_linkRange = 2000.0f;  // link_range: how far a pad may be from its MIK (m)

static char g_dir[MAX_PATH];        // folder of this DLL, trailing backslash
static char g_data[MAX_PATH];       // <dir>spacerace_data\ .
static char g_media[MAX_PATH];      // <game>\media_soviet\ .
static char g_merged[MAX_PATH];     // the merged research.ini
static char g_scenario[64] = "spacerace";
static char g_mission[64]  = "race";
static int  g_autostart = 1;
static int  g_research = 1;
static char g_kit[32] = "9000101";
static int   g_test = 0;            // test_mode: cheap space research, no year limits, the branch open from the start
static float g_testCost = 0.05f;    // test_cost: multiplier on our research costs in test mode

struct Str { int id; wchar_t* text; };
#define MAX_STRINGS 512
static Str g_str[MAX_STRINGS];
static int g_nstr;

static void LogLine(const char* fmt, ...)
{
    char buf[1024];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap);
    H->log("%s", buf);
}

// ------------------------------------------------------------------ files ----

static char* ReadAll(const char* path, size_t* len)
{
    FILE* f = NULL;
    if (fopen_s(&f, path, "rb") != 0 || !f) return NULL;
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (n < 0 || n > 16 * 1024 * 1024) { fclose(f); return NULL; }
    char* buf = (char*)malloc((size_t)n + 1);
    if (!buf) { fclose(f); return NULL; }
    size_t got = fread(buf, 1, (size_t)n, f);
    fclose(f);
    buf[got] = 0;
    if (len) *len = got;
    return buf;
}

static int SameFile(const char* a, const char* b)
{
    WIN32_FILE_ATTRIBUTE_DATA fa, fb;
    if (!GetFileAttributesExA(a, GetFileExInfoStandard, &fa) || !GetFileAttributesExA(b, GetFileExInfoStandard, &fb)) return 0;
    return fa.nFileSizeLow == fb.nFileSizeLow && fa.nFileSizeHigh == fb.nFileSizeHigh &&
           CompareFileTime(&fa.ftLastWriteTime, &fb.ftLastWriteTime) <= 0;
}

// copy src\* into dst\ recursively, skipping files that are already current
static int CopyTree(const char* src, const char* dst)
{
    CreateDirectoryA(dst, NULL);
    char pat[MAX_PATH];
    _snprintf_s(pat, sizeof pat, _TRUNCATE, "%s\\*", src);
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pat, &fd);
    if (h == INVALID_HANDLE_VALUE) return 0;
    int n = 0;
    do
    {
        if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0) continue;
        char s[MAX_PATH], d[MAX_PATH];
        _snprintf_s(s, sizeof s, _TRUNCATE, "%s\\%s", src, fd.cFileName);
        _snprintf_s(d, sizeof d, _TRUNCATE, "%s\\%s", dst, fd.cFileName);
        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) n += CopyTree(s, d);
        else if (!SameFile(s, d) && CopyFileA(s, d, FALSE)) ++n;
    } while (FindNextFileA(h, &fd));
    FindClose(h);
    return n;
}

static void InstallData(void)
{
    char src[MAX_PATH], dst[MAX_PATH];
    _snprintf_s(src, sizeof src, _TRUNCATE, "%sresearch", g_data);
    _snprintf_s(dst, sizeof dst, _TRUNCATE, "%sresearch", g_media);
    int icons = CopyTree(src, dst);
    _snprintf_s(src, sizeof src, _TRUNCATE, "%sscenarios\\%s", g_data, g_scenario);
    _snprintf_s(dst, sizeof dst, _TRUNCATE, "%sscenarios\\%s", g_media, g_scenario);
    int scen = CopyTree(src, dst);
    // icons of the goods the resources plugin adds: the engine looks them up as resources/<name>.png
    _snprintf_s(src, sizeof src, _TRUNCATE, "%sgoods", g_data);
    _snprintf_s(dst, sizeof dst, _TRUNCATE, "%sresources", g_media);
    int goods = CopyTree(src, dst);
    LogLine("spacerace  installed %d research icon(s), %d goods icon(s) and %d scenario file(s) into media_soviet", icons, goods, scen);
}

// ------------------------------------------------------------- research ----

static char* Replace(const char* s, const char* what, const char* with)
{
    size_t lw = strlen(what), lr = strlen(with), n = 0;
    for (const char* p = strstr(s, what); p; p = strstr(p + lw, what)) ++n;
    char* out = (char*)malloc(strlen(s) + n * (lr > lw ? lr - lw : 0) + 1);
    if (!out) return NULL;
    char* o = out;
    const char* p = s;
    for (const char* q = strstr(p, what); q; q = strstr(p, what))
    {
        memcpy(o, p, q - p); o += q - p;
        memcpy(o, with, lr); o += lr;
        p = q + lw;
    }
    strcpy_s(o, strlen(p) + 1, p);
    return out;
}

// insert "\r\n$UNLOCK_RESEARCH child" after the "$RESEARCH parent" line of the vanilla text
static char* Inject(char* text, const char* parent, const char* child, int* ok)
{
    char key[128];
    _snprintf_s(key, sizeof key, _TRUNCATE, "$RESEARCH %s", parent);
    size_t kl = strlen(key);
    for (char* p = strstr(text, key); p; p = strstr(p + 1, key))
    {
        char c = p[kl];
        if (c != '\r' && c != '\n' && c != ' ' && c != '\t') continue;
        char* eol = p + kl;
        while (*eol && *eol != '\n') ++eol;
        char add[160];
        _snprintf_s(add, sizeof add, _TRUNCATE, "\r\n$UNLOCK_RESEARCH %s\r\n", child);
        size_t pre = (size_t)(eol - text) + (*eol ? 1 : 0), al = strlen(add), total = strlen(text);
        char* out = (char*)malloc(total + al + 1);
        if (!out) return text;
        memcpy(out, text, pre);
        memcpy(out + pre, add, al);
        memcpy(out + pre + al, text + pre, total - pre + 1);
        free(text);
        *ok = 1;
        return out;
    }
    *ok = 0;
    return text;
}

// test mode: $COST scaled down, $YEAR dropped, and the first entry marked $AVAILABLE so the
// branch can be researched at once in any start year, without the vanilla engineering chain
static char* TestFilter(const char* text)
{
    size_t n = strlen(text);
    char* out = (char*)malloc(n + 4096);
    if (!out) return NULL;
    char* o = out;
    int first = 1;
    const char* p = text;
    while (*p)
    {
        const char* eol = strchr(p, '\n');
        size_t len = eol ? (size_t)(eol - p + 1) : strlen(p);
        if (strncmp(p, "$YEAR", 5) == 0) { p += len; continue; }
        if (strncmp(p, "$COST ", 6) == 0)
        {
            int c = (int)(atoi(p + 6) * g_testCost);
            if (c < 20) c = 20;
            o += sprintf_s(o, 64, "$COST %d\r\n", c);
            p += len;
            continue;
        }
        memcpy(o, p, len); o += len;
        if (first && strncmp(p, "$RESEARCH ", 10) == 0)
        {
            o += sprintf_s(o, 64, "$AVAILABLE\r\n");
            first = 0;
        }
        p += len;
    }
    *o = 0;
    return out;
}

static int BuildResearch(void)
{
    char path[MAX_PATH];
    _snprintf_s(path, sizeof path, _TRUNCATE, "%sresearch\\research.ini", g_media);
    char* text = ReadAll(path, NULL);
    if (!text) { LogLine("spacerace  cannot read %s - research branch not added", path); return 0; }
    // the vanilla parents gain an unlock line each
    _snprintf_s(path, sizeof path, _TRUNCATE, "%sinject.ini", g_data);
    char* inj = ReadAll(path, NULL);
    int injected = 0;
    if (inj)
    {
        char* ctx = NULL;
        for (char* line = strtok_s(inj, "\r\n", &ctx); line; line = strtok_s(NULL, "\r\n", &ctx))
        {
            if (line[0] == ';' || line[0] == '[') continue;
            char* eq = strchr(line, '=');
            if (!eq) continue;
            *eq = 0;
            char parent[96] = { 0 };
            sscanf_s(line, "%95s", parent, (unsigned)sizeof parent);
            char* ctx2 = NULL;
            for (char* c = strtok_s(eq + 1, ", \t", &ctx2); c; c = strtok_s(NULL, ", \t", &ctx2))
            {
                int ok = 0;
                text = Inject(text, parent, c, &ok);
                if (ok) ++injected;
                else LogLine("spacerace  vanilla research '%s' not found - '%s' has no parent", parent, c);
            }
        }
        free(inj);
    }
    _snprintf_s(path, sizeof path, _TRUNCATE, "%sresearch_space.ini", g_data);
    char* ours = ReadAll(path, NULL);
    if (!ours) { free(text); LogLine("spacerace  no research_space.ini - research branch not added"); return 0; }
    char* ours2 = Replace(ours, "{KIT}", g_kit);
    free(ours);
    if (g_test && ours2)
    {
        char* t = TestFilter(ours2);
        if (t) { free(ours2); ours2 = t; }
        LogLine("spacerace  TEST MODE: space research at %.0f%% cost, no year limits, the branch open from the start", g_testCost * 100.0f);
    }
    FILE* f = NULL;
    if (fopen_s(&f, g_merged, "wb") != 0 || !f) { free(text); free(ours2); LogLine("spacerace  cannot write %s", g_merged); return 0; }
    fwrite(text, 1, strlen(text), f);
    fwrite("\r\n", 1, 2, f);
    if (ours2) fwrite(ours2, 1, strlen(ours2), f);
    fclose(f);
    int entries = 0;
    for (const char* p = ours2 ? strstr(ours2, "$RESEARCH ") : NULL; p; p = strstr(p + 1, "$RESEARCH ")) ++entries;
    free(text); free(ours2);
    LogLine("spacerace  research tree: %d space entries, %d vanilla parent link(s), kit item %s -> %s", entries, injected, g_kit, g_merged);
    return 1;
}

static int IsResearchIni(const char* path)
{
    static const char tail[] = "research/research.ini";
    size_t n = strlen(path), t = sizeof tail - 1;
    if (n < t) return 0;
    const char* p = path + n - t;
    for (size_t i = 0; i < t; ++i)
    {
        char c = p[i];
        if (c == '\\') c = '/';
        if (c >= 'A' && c <= 'Z') c = (char)(c + 32);
        if (c != tail[i]) return 0;
    }
    // media_soviet's own research folder only, never a save's or a workshop item's
    return (n == t) || p[-1] == '/' || p[-1] == '\\';
}

static FILE* __cdecl DetourFopen(const char* path, const char* mode)
{
    if (path && g_merged[0] && IsResearchIni(path))
    {
        FILE* f = g_origFopen(g_merged, mode);
        if (f) return f;
    }
    return g_origFopen(path, mode);
}

// ---------------------------------------------------------------- strings ----

static void LoadStrings(void)
{
    char path[MAX_PATH];
    _snprintf_s(path, sizeof path, _TRUNCATE, "%sstrings.txt", g_data);
    char* text = ReadAll(path, NULL);
    if (!text) { LogLine("spacerace  no strings.txt"); return; }
    char* ctx = NULL;
    for (char* line = strtok_s(text, "\r\n", &ctx); line && g_nstr < MAX_STRINGS; line = strtok_s(NULL, "\r\n", &ctx))
    {
        char* tab = strchr(line, '\t');
        if (!tab) continue;
        *tab = 0;
        int id = atoi(line);
        if (id < STRING_ID_MIN || id > STRING_ID_MAX) continue;
        int wl = MultiByteToWideChar(CP_UTF8, 0, tab + 1, -1, NULL, 0);
        if (wl <= 0) continue;
        wchar_t* w = (wchar_t*)malloc(sizeof(wchar_t) * (size_t)wl);
        if (!w) continue;
        MultiByteToWideChar(CP_UTF8, 0, tab + 1, -1, w, wl);
        g_str[g_nstr].id = id;
        g_str[g_nstr].text = w;
        ++g_nstr;
    }
    free(text);
}

static wchar_t* DetourGetString(void* self, int id)
{
    if (id >= STRING_ID_MIN && id <= STRING_ID_MAX)
        for (int i = 0; i < g_nstr; ++i)
            if (g_str[i].id == id) return g_str[i].text;
    return g_origGetString(self, id);
}

// -------------------------------------------------------------- autostart ----

static const char* StdString(unsigned char* s, size_t* len)
{
    size_t n = *(size_t*)(s + 0x10), cap = *(size_t*)(s + 0x18);
    if (len) *len = n;
    return cap >= 16 ? *(const char**)s : (const char*)s;
}

static void AutoStart(void)
{
    if (!g_autostart) return;
    unsigned char* base = H->exeBase;
    unsigned char* name = base + RVA_SCEN_NAME;
    if (!H->readablePtr(name, 0x20) || !H->readablePtr(base + RVA_SCEN_MISSION, 0x20)) return;
    size_t n = 0;
    const char* cur = StdString(name, &n);
    if (n > 0)
    {
        char tmp[64] = { 0 };
        if (n < sizeof tmp && H->readablePtr(cur, n)) memcpy(tmp, cur, n);
        LogLine("spacerace  world has its own scenario '%s' - programme not started", tmp);
        return;
    }
    char check[MAX_PATH];
    _snprintf_s(check, sizeof check, _TRUNCATE, "%sscenarios\\%s\\%s\\script.ini", g_media, g_scenario, g_mission);
    if (GetFileAttributesA(check) == INVALID_FILE_ATTRIBUTES)
    {
        LogLine("spacerace  %s missing - programme not started", check);
        return;
    }
    StrAssignFn assign = (StrAssignFn)(base + RVA_STR_ASSIGN);
    assign(name, g_scenario, strlen(g_scenario));
    assign(base + RVA_SCEN_MISSION, g_mission, strlen(g_mission));
    *(unsigned char*)(base + RVA_SCEN_AUTOSTART) = 1;
    LogLine("spacerace  ordinary game: auto-starting scenario %s / %s", g_scenario, g_mission);
}

static void* DetourEnum(void* a, void* b, void* c, void* d)
{
    __try { AutoStart(); }
    __except (H->faultFilter("spacerace", GetExceptionInformation())) {}
    return g_origEnum(a, b, c, d);
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
                           (LPCSTR)&LoadConfig, &self) && GetModuleFileNameA(self, g_dir, MAX_PATH))
    {
        char* slash = strrchr(g_dir, '\\');
        if (slash) slash[1] = 0;
    }
    _snprintf_s(g_data, sizeof g_data, _TRUNCATE, "%sspacerace_data\\", g_dir);
    _snprintf_s(g_merged, sizeof g_merged, _TRUNCATE, "%sresearch_merged.ini", g_data);
    char exe[MAX_PATH] = { 0 };
    GetModuleFileNameA(NULL, exe, MAX_PATH);
    char* slash = strrchr(exe, '\\');
    if (slash) slash[1] = 0;
    _snprintf_s(g_media, sizeof g_media, _TRUNCATE, "%smedia_soviet\\", exe);

    char path[MAX_PATH];
    _snprintf_s(path, sizeof path, _TRUNCATE, "%sspacerace.ini", g_dir);
    FILE* f = NULL;
    if (fopen_s(&f, path, "r") != 0 || !f) { LogLine("spacerace  no spacerace.ini - defaults"); return; }
    char line[256];
    while (fgets(line, sizeof line, f))
    {
        char* semi = strchr(line, ';'); if (semi) *semi = 0;
        Trim(line);
        if (!line[0] || line[0] == '[') continue;
        char* eq = strchr(line, '='); if (!eq) continue;
        *eq = 0; char* key = line; char* val = eq + 1;
        Trim(key); Trim(val);
        if      (_stricmp(key, "kit_item") == 0)  strncpy_s(g_kit, sizeof g_kit, val, _TRUNCATE);
        else if (_stricmp(key, "autostart") == 0) g_autostart = atoi(val);
        else if (_stricmp(key, "research") == 0)  g_research = atoi(val);
        else if (_stricmp(key, "scenario") == 0)  strncpy_s(g_scenario, sizeof g_scenario, val, _TRUNCATE);
        else if (_stricmp(key, "mission") == 0)   strncpy_s(g_mission, sizeof g_mission, val, _TRUNCATE);
        else if (_stricmp(key, "test_mode") == 0) g_test = atoi(val);
        else if (_stricmp(key, "test_cost") == 0) { float v = (float)atof(val); if (v > 0.0f) g_testCost = v; }
        else if (_stricmp(key, "link_range") == 0) { float v = (float)atof(val); if (v > 0.0f) g_linkRange = v; }
    }
    fclose(f);
}

// ------------------------------------------------------------ pad links ----

static int Readable(const void* p, size_t n) { return p && H->readablePtr(p, n); }

static int LooksLikePointer(const void* p)
{
    ULONG_PTR v = (ULONG_PTR)p;
    if (v < 0x10000 || v > 0x00007FFFFFFFFFFFull || (v & 7)) return 0;
    return H->readablePtr(p, 16);
}

// the object part of a building's type ident ("9000101/sr_mik" -> "sr_mik") and its building type
static const char* ObjectOf(unsigned char* b, int* type)
{
    if (!Readable(b + BLD_TYPEDESC, 8)) return NULL;
    unsigned char* td = *(unsigned char**)(b + BLD_TYPEDESC);
    if (!LooksLikePointer(td) || !Readable(td, 0x40) || !Readable(td + TD_TYPE, 4)) return NULL;
    const char* s = (const char*)td;
    int i = 0;
    for (; i < 0x40 && s[i]; ++i)
        if (s[i] < 0x20 || s[i] > 0x7E) return NULL;
    if (i < 2 || i >= 0x40) return NULL;
    *type = *(int*)(td + TD_TYPE);
    const char* slash = strrchr(s, '/');
    return slash ? slash + 1 : s;
}

static int Position(unsigned char* b, float* x, float* z)
{
    unsigned char* node = b + BLD_NODE;
    if (!g_getPos || !Readable(node, 0x100)) return 0;
    float out[4] = { 0, 0, 0, 0 };
    float* r = g_getPos(node, out);
    if (!r) return 0;
    *x = r[0]; *z = r[2];
    return 1;
}

static void LinkPads(unsigned char* ctx)
{
    if (!Readable(ctx + CTX_BUILDINGS, 16)) return;
    unsigned char** begin = *(unsigned char***)(ctx + CTX_BUILDINGS);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_BUILDINGS + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    if (n > 200000) return;
    enum { MAX_MIK = 64 };
    unsigned char* mik[MAX_MIK]; float mx[MAX_MIK], mz[MAX_MIK]; int nmik = 0;
    for (SIZE_T i = 0; i < n && nmik < MAX_MIK; ++i)
    {
        unsigned char* b = begin[i];
        int type = -1;
        const char* obj = LooksLikePointer(b) ? ObjectOf(b, &type) : NULL;
        if (obj && type == TYPE_PRODUCTION && _stricmp(obj, "sr_mik") == 0 && Position(b, &mx[nmik], &mz[nmik]))
            mik[nmik++] = b;
    }
    if (!nmik) return;
    AddChildFn addChild = (AddChildFn)(H->exeBase + RVA_ADD_CHILD);
    for (SIZE_T i = 0; i < n; ++i)
    {
        unsigned char* b = begin[i];
        int type = -1;
        const char* obj = LooksLikePointer(b) ? ObjectOf(b, &type) : NULL;
        if (!obj || type != TYPE_AIR_PARKING || _strnicmp(obj, "sr_pad_", 7) != 0) continue;
        if (!Readable(b + BLD_PARENT, 8) || *(void**)(b + BLD_PARENT)) continue;
        float x, z;
        if (!Position(b, &x, &z)) continue;
        int best = -1; float bestD = g_linkRange * g_linkRange;
        for (int k = 0; k < nmik; ++k)
        {
            float d = (mx[k] - x) * (mx[k] - x) + (mz[k] - z) * (mz[k] - z);
            if (d <= bestD) { bestD = d; best = k; }
        }
        if (best < 0) continue;
        *(unsigned char**)(b + BLD_PARENT) = mik[best];
        addChild(ctx, mik[best], b);
        LogLine("spacerace  linked launch pad %s to the MIK %.0f m away - finished rockets roll out onto it", obj, sqrtf(bestD));
    }
}

// ------------------------------------------------------------- launches ----
//
// The programme cannot take goods out of a building (the VM's Resources calls
// only read) and has no way to animate a vehicle, so a launch is split: when
// everything is in place the script flags the rocket with
// Vehicle_SetCanSell(rocket, 0) - the one vehicle write the VM has, a byte at
// vehicle+0x38A - waits while it climbs, then removes it with Vehicle_Sell.
// This code watches the vehicle list for a flagged rocket, takes its launch
// load (launches.ini) out of storage buildings within the radius of the pad,
// and lifts it: both world matrices a vehicle keeps (+0xD60 and +0x1080, rows
// then translation, each followed by its inverse) and the position copies at
// +0xDE0 / +0x1100 get the new height every tick. A parked vehicle's matrices
// are not recomputed by the game (tested: a raised value stays). When the climb
// is over the flag is cleared again; the script sees vehi.bDisableSell drop and
// removes the rocket (a failure removes it after a few seconds instead).

#define CTX_VEHICLES       0x12810
#define VEH_TYPE           0x1708
#define VEH_NOSELL         0x38A
#define VT_IDENT           0x200
#define TYPE_STORAGE       5
#define MAX_ROCKETS        16
#define MAX_LAUNCHES       8

#define MAX_GOODS          6
struct GoodT { char name[32]; float t; };
struct RocketLoad
{
    char  object[32];
    char  pad[32];                 // the only pad kind it may stand on
    GoodT load[MAX_GOODS]; int nload;   // taken from storages at lift-off
    GoodT bill[MAX_GOODS]; int nbill;   // what the MIK builds it from (replaces the engine's weight-based bill)
};
static RocketLoad g_rocket[MAX_ROCKETS];
static int   g_nrocket;
// added goods scripts may read: the name -> Resources-field chain (SOVIET64 0x59B3F0) knows only the
// base game's names, so these are answered with the spare fields _Resources_reserved_16_.._19_
static char  g_vmGoods[4][32];
static int   g_nvm;
static float g_launchRadius = 450.0f;
static float g_climbSeconds = 18.0f;

struct Launch
{
    unsigned char* v;
    float t;                     // seconds of climb so far
    float rows[2][3][3];         // rotation rows of the two world matrices
    float base[2][3];            // their translations at lift-off
    int   done;                  // climb finished; wait for the script to remove it
};
static Launch g_launch[MAX_LAUNCHES];
static int    g_nlaunch;
static ULONGLONG g_lastTickMs;

// Particles: the engine's effect library (particleeffects.ini) hangs off the global C3D
// object at SOVIET64 RVA 0x9941F0, +0xF60. Effects are looked up by name and emitted
// with C3D_PARTICLEFFECT::SpawnParticles(pos, dir, 1, 1.0, 1.0, 0) - the game's own
// calls (vehicle dust 0x16CB6B, weather 0xEB87). Vehicles only emit their
// $PARTICLE_MOVEMENT while the game moves them, so a launch spawns its own.
#define RVA_ENGINE_PTR     0x9941F0
#define ENG_PARTICLES      0xF60
typedef void* (*GetEffectFn)(void* lib, char* name);
typedef void  (*SpawnFn)(void* effect, const float* pos, const float* dir, char a, float b, float c, char d);
static GetEffectFn g_getEffect;
static SpawnFn     g_spawn;
static char g_fxFlame[32] = "airplane_jet";      // under the rocket, every tick of the climb
static char g_fxSmoke[32] = "big_firesmoke";     // the trail
static char g_fxPad[32]   = "factory_big_white"; // steam and dust round the pad as it lifts off
static char g_fxBoom[32]  = "buildingfall2";     // a failed rocket
struct Aftermath { float x, y, z, left; };
#define MAX_AFTER 8
static Aftermath g_after[MAX_AFTER];
static int g_nafter;

static void Fx(char* name, float x, float y, float z, float dy)
{
    if (!g_getEffect || !g_spawn || !name[0]) return;
    unsigned char* eng = *(unsigned char**)(H->exeBase + RVA_ENGINE_PTR);
    if (!LooksLikePointer(eng) || !Readable(eng + ENG_PARTICLES, 8)) return;
    void* lib = *(void**)(eng + ENG_PARTICLES);
    if (!LooksLikePointer(lib)) return;
    void* fx = g_getEffect(lib, name);
    if (!fx) return;
    float pos[3] = { x, y, z }, dir[3] = { 0.0f, dy, 0.0f };
    g_spawn(fx, pos, dir, 1, 1.0f, 1.0f, 0);
}

static void LoadLaunches(void)
{
    char path[MAX_PATH];
    _snprintf_s(path, sizeof path, _TRUNCATE, "%slaunches.ini", g_data);
    FILE* f = NULL;
    if (fopen_s(&f, path, "r") != 0 || !f) { LogLine("spacerace  no launches.ini - launches will take no goods"); return; }
    char line[512];
    while (fgets(line, sizeof line, f))
    {
        char* semi = strchr(line, ';'); if (semi) *semi = 0;
        char tok[16][32]; int n = 0;
        for (char* ctx = NULL, *t = strtok_s(line, " \t\r\n", &ctx); t && n < 16; t = strtok_s(NULL, " \t\r\n", &ctx))
            strncpy_s(tok[n++], 32, t, _TRUNCATE);
        if (n < 2) continue;
        const char* key = tok[0]; const char* a = tok[1];
        if (_stricmp(key, "rocket") == 0 && n >= 3 && g_nrocket < MAX_ROCKETS)
        {
            RocketLoad* r = &g_rocket[g_nrocket++];
            memset(r, 0, sizeof *r);
            strncpy_s(r->object, sizeof r->object, tok[1], _TRUNCATE);
            strncpy_s(r->pad, sizeof r->pad, tok[2], _TRUNCATE);
            for (int k = 3; k + 1 < n && r->nload < MAX_GOODS; k += 2)
            {
                strncpy_s(r->load[r->nload].name, 32, tok[k], _TRUNCATE);
                r->load[r->nload++].t = (float)atof(tok[k + 1]);
            }
        }
        else if (_stricmp(key, "bill") == 0 && n >= 4)
        {
            for (int i = 0; i < g_nrocket; ++i)
            {
                if (_stricmp(g_rocket[i].object, tok[1]) != 0) continue;
                RocketLoad* r = &g_rocket[i];
                r->nbill = 0;
                for (int k = 2; k + 1 < n && r->nbill < MAX_GOODS; k += 2)
                {
                    strncpy_s(r->bill[r->nbill].name, 32, tok[k], _TRUNCATE);
                    r->bill[r->nbill++].t = (float)atof(tok[k + 1]);
                }
            }
        }
        else if (_stricmp(key, "vm_goods") == 0)
        {
            g_nvm = 0;
            for (int k = 1; k < n && g_nvm < 4; ++k) strncpy_s(g_vmGoods[g_nvm++], 32, tok[k], _TRUNCATE);
        }
        else if (_stricmp(key, "radius") == 0) g_launchRadius = (float)atof(a);
        else if (_stricmp(key, "climb_seconds") == 0) g_climbSeconds = (float)atof(a);
        else if (_stricmp(key, "fx_flame") == 0) strncpy_s(g_fxFlame, 32, a, _TRUNCATE);
        else if (_stricmp(key, "fx_smoke") == 0) strncpy_s(g_fxSmoke, 32, a, _TRUNCATE);
        else if (_stricmp(key, "fx_pad") == 0)   strncpy_s(g_fxPad, 32, a, _TRUNCATE);
        else if (_stricmp(key, "fx_boom") == 0)  strncpy_s(g_fxBoom, 32, a, _TRUNCATE);
    }
    fclose(f);
    int bills = 0;
    for (int i = 0; i < g_nrocket; ++i) bills += g_rocket[i].nbill > 0;
    LogLine("spacerace  launches: %d rockets (%d with a bill of parts), %d goods visible to scripts, storages within %.0f m, %.0f s climb",
            g_nrocket, bills, g_nvm, g_launchRadius, g_climbSeconds);
}

static const RocketLoad* RocketOf(unsigned char* v)
{
    if (!Readable(v + VEH_TYPE, 8)) return NULL;
    unsigned char* vt = *(unsigned char**)(v + VEH_TYPE);
    if (!LooksLikePointer(vt) || !Readable(vt + VT_IDENT, 48)) return NULL;
    const char* s = (const char*)(vt + VT_IDENT);
    if (!memchr(s, 0, 48)) return NULL;
    const char* slash = strrchr(s, '/');
    const char* obj = slash ? slash + 1 : s;
    for (int i = 0; i < g_nrocket; ++i)
        if (_stricmp(obj, g_rocket[i].object) == 0) return &g_rocket[i];
    return NULL;
}

// takes the rocket's load from storage buildings within the radius; got[] is what it found
static void TakeLoad(unsigned char* ctx, float x, float z, const RocketLoad* r, float got[MAX_GOODS])
{
    float need[MAX_GOODS];
    for (int k = 0; k < MAX_GOODS; ++k) { need[k] = k < r->nload ? r->load[k].t : 0.0f; got[k] = 0.0f; }
    unsigned char** begin = *(unsigned char***)(ctx + CTX_BUILDINGS);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_BUILDINGS + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    for (SIZE_T i = 0; i < n && n < 200000; ++i)
    {
        unsigned char* b = begin[i];
        int type = -1;
        if (!LooksLikePointer(b) || !ObjectOf(b, &type) || type != TYPE_STORAGE) continue;
        float bx, bz;
        if (!Position(b, &bx, &bz) || (bx - x) * (bx - x) + (bz - z) * (bz - z) > g_launchRadius * g_launchRadius) continue;
        if (!Readable(b + 0x970, 16)) continue;
        unsigned char* sb0 = *(unsigned char**)(b + 0x970);
        unsigned char* se0 = *(unsigned char**)(b + 0x978);
        if (!LooksLikePointer(sb0) || se0 < sb0 || (SIZE_T)(se0 - sb0) > 32 * 0xE0) continue;
        for (unsigned char* rec = sb0; rec < se0; rec += 0xE0)
        {
            if (!Readable(rec, 16)) continue;
            unsigned char* sb = *(unsigned char**)(rec + 0);
            unsigned char* se = *(unsigned char**)(rec + 8);
            if (!LooksLikePointer(sb) || se < sb || (SIZE_T)(se - sb) > 0x800) continue;
            for (unsigned char* sl = sb; sl < se; sl += 16)
            {
                if (!Readable(sl, 16)) continue;
                unsigned char* res = *(unsigned char**)sl;
                if (!LooksLikePointer(res) || !Readable(res, 32)) continue;
                float* content = (float*)(sl + 8);
                for (int k = 0; k < r->nload; ++k)
                {
                    if (need[k] <= 0.0f || _stricmp((const char*)res, r->load[k].name) != 0) continue;
                    float t = *content < need[k] ? *content : need[k];
                    if (t <= 0.0f) continue;
                    *content -= t; need[k] -= t; got[k] += t;
                }
            }
        }
    }
}

static void Place(Launch* L, float h)
{
    static const int kMat[2] = { 0xD60, 0x1080 }, kCopy[2] = { 0xDE0, 0x1100 };
    for (int m = 0; m < 2; ++m)
    {
        float t[3] = { L->base[m][0], L->base[m][1] + h, L->base[m][2] };
        float* W = (float*)(L->v + kMat[m]);          // 4x4 row-major: rows 0-2 rotation, row 3 translation
        float* I = W + 16;                            // its inverse follows
        W[12] = t[0]; W[13] = t[1]; W[14] = t[2];
        for (int j = 0; j < 3; ++j)                   // inverse translation = -(t . row j)
            I[12 + j] = -(t[0] * L->rows[m][j][0] + t[1] * L->rows[m][j][1] + t[2] * L->rows[m][j][2]);
        float* c = (float*)(L->v + kCopy[m]);
        c[0] = t[0]; c[1] = t[1]; c[2] = t[2];
    }
}

static void Launches(unsigned char* ctx, int scan)
{
    if (!g_nrocket || !Readable(ctx + CTX_VEHICLES, 16)) return;
    unsigned char** begin = *(unsigned char***)(ctx + CTX_VEHICLES);
    unsigned char** end   = *(unsigned char***)(ctx + CTX_VEHICLES + 8);
    if (!LooksLikePointer(begin) || end < begin) return;
    SIZE_T n = (SIZE_T)(end - begin);
    if (n > 200000) return;
    ULONGLONG now = GetTickCount64();
    float dt = g_lastTickMs ? (float)(now - g_lastTickMs) / 1000.0f : 0.0f;
    if (dt > 0.1f) dt = 0.1f;                         // a pause or a hitch does not jump the rocket
    g_lastTickMs = now;

    // drop launches whose rocket the script has removed; one removed mid-climb blew up
    for (int i = 0; i < g_nlaunch; )
    {
        int alive = 0;
        for (SIZE_T k = 0; k < n && !alive; ++k) alive = (begin[k] == g_launch[i].v);
        if (!alive)
        {
            Launch* L = &g_launch[i];
            if (!L->done && g_nafter < MAX_AFTER)
            {
                float s = L->t, h = 1.2f * s * s + 0.25f * s * s * s;
                Aftermath* A = &g_after[g_nafter++];
                A->x = L->base[0][0]; A->y = L->base[0][1] + h; A->z = L->base[0][2]; A->left = 8.0f;
                for (int b = 0; b < 4; ++b) Fx(g_fxBoom, A->x, A->y + 4.0f * b, A->z, 1.0f);
            }
            g_launch[i] = g_launch[--g_nlaunch];
            continue;
        }
        ++i;
    }
    // an explosion keeps smoking for a few seconds
    for (int i = 0; i < g_nafter; )
    {
        Aftermath* A = &g_after[i];
        if ((A->left -= dt) <= 0.0f) { g_after[i] = g_after[--g_nafter]; continue; }
        if (g_ticks % 3 == 0) Fx(g_fxSmoke, A->x, A->y, A->z, 1.0f);
        ++i;
    }
    // climb
    for (int i = 0; i < g_nlaunch; ++i)
    {
        Launch* L = &g_launch[i];
        if (!L->done && (L->t += dt) >= g_climbSeconds)
        {
            L->t = g_climbSeconds;
            L->done = 1;
            if (Readable(L->v + VEH_NOSELL, 1)) *(L->v + VEH_NOSELL) = 0;   // tells the script (vehi.bDisableSell) the climb is over
        }
        float s = L->t, h = 1.2f * s * s + 0.25f * s * s * s;  // slow off the pad, then faster: ~60 m at 5 s, ~370 m at 10 s
        Place(L, h);
        if (!L->done)
        {
            float x = L->base[0][0], y = L->base[0][1] + h, z = L->base[0][2];
            for (int k = 0; k < 3; ++k) Fx(g_fxFlame, x, y - 2.0f * k, z, -1.0f);    // a column of flame below the nozzles
            Fx(g_fxSmoke, x, y - 7.0f, z, -1.0f);
            if (s < 4.0f && g_ticks % 2 == 1) Fx(g_fxPad, x, L->base[0][1], z, 1.0f);
        }
    }
    if (!scan) return;
    // new launch requests: a rocket the programme has flagged
    for (SIZE_T k = 0; k < n && g_nlaunch < MAX_LAUNCHES; ++k)
    {
        unsigned char* v = begin[k];
        if (!LooksLikePointer(v) || !Readable(v + VEH_NOSELL, 1) || !*(v + VEH_NOSELL)) continue;
        const RocketLoad* r = RocketOf(v);
        if (!r || !Readable(v + 0xD60, 0x3C0)) continue;
        int known = 0;
        for (int i = 0; i < g_nlaunch && !known; ++i) known = (g_launch[i].v == v);
        if (known) continue;
        Launch* L = &g_launch[g_nlaunch++];
        memset(L, 0, sizeof *L);
        L->v = v;
        static const int kMat[2] = { 0xD60, 0x1080 };
        for (int m = 0; m < 2; ++m)
        {
            const float* W = (const float*)(v + kMat[m]);
            for (int j = 0; j < 3; ++j) for (int c = 0; c < 3; ++c) L->rows[m][j][c] = W[j * 4 + c];
            L->base[m][0] = W[12]; L->base[m][1] = W[13]; L->base[m][2] = W[14];
        }
        float got[MAX_GOODS];
        TakeLoad(ctx, L->base[0][0], L->base[0][2], r, got);
        char took[256] = { 0 };
        for (int k = 0; k < r->nload; ++k)
        {
            char part[64];
            _snprintf_s(part, sizeof part, _TRUNCATE, "%s%.1f/%.1f t %s", k ? ", " : "", got[k], r->load[k].t, r->load[k].name);
            strcat_s(took, sizeof took, part);
        }
        LogLine("spacerace  lift-off: %s took %s from storages within %.0f m", r->object, took, g_launchRadius);
    }
}

const RocketLoad* RocketType(unsigned char* vt);

// Scripts read goods through Resources.GetFromBuilding and friends, which place each good by
// asking SOVIET64 0x59B3F0(vm, name) for its byte offset in the Resources struct: a chain of
// compares against the base game's names that answers 0 (the `workers` field!) for anything else.
// The configured vm_goods get the four spare floats after service_material (0xE8) instead.
#define RVA_RES_FIELD      0x59B3F0
static const unsigned char kResFieldPro[15] = { 0x48, 0x89, 0x5C, 0x24, 0x08, 0x57, 0x48, 0x83, 0xEC, 0x20, 0x33, 0xDB,
                                                0x48, 0x8B, 0xFA };
typedef int (*ResFieldFn)(void* vm, const char* name);
static ResFieldFn g_origResField;

static int DetourResField(void* vm, const char* name)
{
    __try
    {
        if (name && H->readablePtr(name, 32))
            for (int i = 0; i < g_nvm; ++i)
                if (strcmp(name, g_vmGoods[i]) == 0) return 0xEC + 4 * i;
    }
    __except (H->faultFilter("spacerace", GetExceptionInformation())) {}
    return g_origResField(vm, name);
}

// A rocket's bill of parts. The engine computes every vehicle's bill from its empty weight in
// fixed vanilla goods (0x3F8D10: workers, steel, aluminium, plastics, ...) into a vector at
// vehicle type +0x85C8 of { Resource*, float tonnes, pad } - there is no script token for it.
// For each rocket with a `bill` line the vector is rewritten in place: the workers entry stays,
// the rest become the bill's goods (never more entries than it had). Checked every couple of
// seconds, so a type the engine rebuilds is rewritten again.
#define RVA_RES_VECTOR     0x9E11C0
#define RES_STRIDE_BYTES   832
#define RVA_VEH_TYPES      0x9E7750
#define VT_STRIDE          0x9F08
#define VT_BILL            0x85C8

static unsigned char* ResourceByName(const char* name)
{
    unsigned char* b = *(unsigned char**)(H->exeBase + RVA_RES_VECTOR);
    unsigned char* e = *(unsigned char**)(H->exeBase + RVA_RES_VECTOR + 8);
    if (!LooksLikePointer(b) || e < b || (SIZE_T)(e - b) > 512 * RES_STRIDE_BYTES) return NULL;
    for (unsigned char* r = b; r + RES_STRIDE_BYTES <= e; r += RES_STRIDE_BYTES)
        if (Readable(r, 32) && strncmp((const char*)r, name, 32) == 0) return r;
    return NULL;
}

static int g_billsDone;

static void RewriteBills(void)
{
    unsigned char* b = *(unsigned char**)(H->exeBase + RVA_VEH_TYPES);
    unsigned char* e = *(unsigned char**)(H->exeBase + RVA_VEH_TYPES + 8);
    if (!LooksLikePointer(b) || e < b || (SIZE_T)(e - b) > 20000 * (SIZE_T)VT_STRIDE) return;
    unsigned char* workers = ResourceByName("workers");
    int done = 0;
    for (unsigned char* vt = b; vt + VT_STRIDE <= e; vt += VT_STRIDE)
    {
        const RocketLoad* r = RocketType(vt);
        if (!r || !r->nbill || !Readable(vt + VT_BILL, 24)) continue;
        if (strncmp((const char*)(vt + VT_IDENT), "shadow", 6) == 0) continue;   // the engine's shadow copies of each type
        unsigned char* vb = *(unsigned char**)(vt + VT_BILL);
        unsigned char* ve = *(unsigned char**)(vt + VT_BILL + 8);
        if (!LooksLikePointer(vb) || ve < vb || (SIZE_T)(ve - vb) > 64 * 16 || !Readable(vb, ve - vb)) continue;
        int have = (int)((ve - vb) / 16);
        // already ours?
        int ours = 1, k = 0;
        for (int i = 0; i < have; ++i)
        {
            unsigned char* res = *(unsigned char**)(vb + i * 16);
            if (res == workers) continue;
            if (k >= r->nbill || !res || strncmp((const char*)res, r->bill[k].name, 32) != 0) { ours = 0; break; }
            ++k;
        }
        if (ours && k == r->nbill) { ++done; continue; }
        // workers first, then the bill
        unsigned char* goods[MAX_GOODS]; int ng = 0;
        for (int i = 0; i < r->nbill; ++i)
        {
            goods[ng] = ResourceByName(r->bill[i].name);
            if (!goods[ng]) { LogLine("spacerace  bill for %s: no good called %s - is the resources plugin on?", r->object, r->bill[i].name); return; }
            ++ng;
        }
        float workdays = 0.0f;
        for (int i = 0; i < have; ++i)
            if (*(unsigned char**)(vb + i * 16) == workers) workdays = *(float*)(vb + i * 16 + 8);
        int slots = have - (workdays > 0.0f ? 1 : 0);
        if (slots < ng) { LogLine("spacerace  bill for %s: room for %d goods, the bill has %d - left as the engine made it", r->object, slots, ng); continue; }
        int w = 0;
        if (workdays > 0.0f) { *(unsigned char**)(vb) = workers; *(float*)(vb + 8) = workdays; w = 1; }
        for (int i = 0; i < ng; ++i, ++w) { *(unsigned char**)(vb + w * 16) = goods[i]; *(float*)(vb + w * 16 + 8) = r->bill[i].t; }
        *(unsigned char**)(vt + VT_BILL + 8) = vb + w * 16;       // shorter: the rest of the block stays allocated
        ++done;
        LogLine("spacerace  bill for %s: %.0f workdays + %d goods (was %d entries)", r->object, workdays, ng, have);
    }
    g_billsDone = done;
}

// Which vehicle may use which pad. SOVIET64 0x3E2900(game, building, vehicle type, flag, x)
// answers "may this vehicle type use this building" for the purchase list, assignments and a
// production line choosing where a finished vehicle goes (0x1CA9FB). Launch pads take only the
// rockets launches.ini gives them (the N1 its heavy complex, the others the R-7 pad); the
// recovery field takes no rockets. Everything else is the game's own answer.
#define RVA_CAN_USE        0x3E2900
static const unsigned char kCanUsePro[23] = { 0x48, 0x89, 0x5C, 0x24, 0x10, 0x48, 0x89, 0x6C, 0x24, 0x18, 0x44, 0x88,
                                              0x4C, 0x24, 0x20, 0x56, 0x57, 0x41, 0x54, 0x41, 0x55, 0x41, 0x56 };
typedef char (*CanUseFn)(void* ctx, unsigned char* bld, unsigned char* vt, char flag, void* extra);
static CanUseFn g_origCanUse;
static unsigned g_padRefusals;

const RocketLoad* RocketType(unsigned char* vt)
{
    if (!LooksLikePointer(vt) || !Readable(vt + VT_IDENT, 48)) return NULL;
    const char* s = (const char*)(vt + VT_IDENT);
    if (!memchr(s, 0, 48)) return NULL;
    const char* slash = strrchr(s, '/');
    const char* obj = slash ? slash + 1 : s;
    for (int i = 0; i < g_nrocket; ++i)
        if (_stricmp(obj, g_rocket[i].object) == 0) return &g_rocket[i];
    return NULL;
}

static int PadAllows(unsigned char* bld, unsigned char* vt)
{
    int type = -1;
    const char* bo = LooksLikePointer(bld) ? ObjectOf(bld, &type) : NULL;
    if (!bo) return -1;
    int pad = _strnicmp(bo, "sr_pad_", 7) == 0, recovery = _stricmp(bo, "sr_recovery") == 0;
    if (!pad && !recovery) return -1;
    const RocketLoad* r = RocketType(vt);
    if (recovery) return r ? 0 : -1;
    return (r && r->pad[0] && _stricmp(r->pad, bo) == 0) ? 1 : 0;
}

static char DetourCanUse(void* ctx, unsigned char* bld, unsigned char* vt, char flag, void* extra)
{
    int allow = -1;
    __try { allow = PadAllows(bld, vt); }
    __except (H->faultFilter("spacerace", GetExceptionInformation())) { allow = -1; }
    if (allow == 0) { ++g_padRefusals; return 0; }
    return g_origCanUse(ctx, bld, vt, flag, extra);
}

static void DetourTick(void* ctx)
{
    g_origTick(ctx);
    ++g_ticks;
    __try
    {
        Launches((unsigned char*)ctx, (g_ticks % 10) == 0);
        if (g_ticks % 120 == 0) { LinkPads((unsigned char*)ctx); RewriteBills(); }
    }
    __except (H->faultFilter("spacerace", GetExceptionInformation())) {}
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
    info->name    = "spacerace";
    info->version = "0.1";
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    LoadConfig();
    InstallData();
    LoadStrings();
    LoadLaunches();
    int hooks = 0;
    if (g_research && BuildResearch())
    {
        if (H->patchIat(H->exeBase, "api-ms-win-crt-stdio-l1-1-0.dll", "fopen", (void*)&DetourFopen, (void**)&g_origFopen, "spacerace fopen"))
            ++hooks;
        else
            LogLine("spacerace  could not swap the fopen import - research branch not added");
    }
    if (H->patchIat(H->exeBase, "C3DDLL64.dll", "?GetString@C3D_LANGUAGE@@QEAAPEA_WH@Z", (void*)&DetourGetString, (void**)&g_origGetString, "spacerace GetString"))
        ++hooks;
    else
        LogLine("spacerace  could not swap the GetString import - research names will be missing");
    unsigned char live[18];
    const unsigned char* expect = LiveOrPristine(H->exeBase + RVA_SCEN_ENUM, kEnumPro, 18, live, "spacerace ScenarioEnumeration");
    if (H->installInlineHook(H->exeBase + RVA_SCEN_ENUM, (void*)&DetourEnum, (void**)&g_origEnum, expect, 18, "spacerace ScenarioEnumeration"))
        ++hooks;
    else
        LogLine("spacerace  scenario enumeration 0x%X did not match - the programme will not start itself", RVA_SCEN_ENUM);
    HMODULE c3d = GetModuleHandleA("C3DDLL64.dll");
    if (c3d) g_getPos = (GetPositionFn)GetProcAddress(c3d, "?GetPosition@C3D_NODE@@QEAA?AVC3DVECTOR3@@XZ");
    if (c3d)
    {
        g_getEffect = (GetEffectFn)GetProcAddress(c3d, "?GetEffect@C3D_PARTICLEFFECT_LIBRARY@@QEAAPEAVC3D_PARTICLEFFECT@@PEAD@Z");
        g_spawn     = (SpawnFn)GetProcAddress(c3d, "?SpawnParticles@C3D_PARTICLEFFECT@@QEAAXVC3DVECTOR3@@0_NMM1@Z");
    }
    // other RML plugins (helicopter distribution office, rolling stock road transport) hook this
    // too, with a 14-byte absolute jump (FF 25 00000000 <address>): chain on exactly that jump
    if (g_nvm)
    {
        unsigned char liveRes[15];
        const unsigned char* expectRes = LiveOrPristine(H->exeBase + RVA_RES_FIELD, kResFieldPro, 15, liveRes, "spacerace ResourceField");
        if (H->installInlineHook(H->exeBase + RVA_RES_FIELD, (void*)&DetourResField, (void**)&g_origResField, expectRes, 15, "spacerace ResourceField"))
            ++hooks;
        else
            LogLine("spacerace  script goods not hooked - the programme cannot see %s and the rest", g_vmGoods[0]);
    }
    unsigned char liveCan[23];
    const unsigned char* expectCan = kCanUsePro;
    size_t lenCan = 23;
    unsigned char* tCan = (unsigned char*)(H->exeBase + RVA_CAN_USE);
    static const unsigned char kAbsJmp[6] = { 0xFF, 0x25, 0x00, 0x00, 0x00, 0x00 };
    if (H->readablePtr(tCan, 23) && memcmp(tCan, kAbsJmp, 6) == 0)
    {
        memcpy(liveCan, tCan, 14);
        expectCan = liveCan; lenCan = 14;
        LogLine("spacerace CanUseBuilding: another plugin's jump is there, chaining after it");
    }
    else
        expectCan = LiveOrPristine(tCan, kCanUsePro, 23, liveCan, "spacerace CanUseBuilding");
    if (g_nrocket && H->installInlineHook(tCan, (void*)&DetourCanUse, (void**)&g_origCanUse, expectCan, lenCan, "spacerace CanUseBuilding"))
        ++hooks;
    else
        LogLine("spacerace  vehicle-building check not hooked - any rocket can use any pad");
    unsigned char liveTick[19];
    const unsigned char* expectTick = LiveOrPristine(H->exeBase + RVA_TICK_ALL, kTickPro, 19, liveTick, "spacerace TickAllBuildings");
    if (g_getPos && H->installInlineHook(H->exeBase + RVA_TICK_ALL, (void*)&DetourTick, (void**)&g_origTick, expectTick, 19, "spacerace TickAllBuildings"))
        ++hooks;
    else
        LogLine("spacerace  TickAllBuildings hook not installed - launch pads will not be linked to the MIK");
    LogLine("spacerace  active: %d/%d hooks, %d strings, autostart %s, pads link to a MIK within %.0f m, launch effects %s",
            hooks, g_nvm ? 6 : 5, g_nstr, g_autostart ? "on" : "off", g_linkRange, (g_getEffect && g_spawn) ? "on" : "OFF (exports not found)");
    return 0;
}

BOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }
