"""Port vendor/TesmioLoader/plugins/resources/resources.cpp into mod/plugins/resources for RML.
Re-runnable: always starts from the vendored file."""
import os

SRC = 'vendor/TesmioLoader/plugins/resources/resources.cpp'
DST = 'mod/plugins/resources/resources.cpp'
s = open(SRC, encoding='utf-8').read()


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (old[:70], s.count(old))
    s = s.replace(old, new)


header = '''// resources.cpp - ported from vendor/TesmioLoader/plugins/resources (v1.7) for the
// Republic Mod Loader, as part of the Space Race package. Changes from the vendored file:
//   - resources.ini is read from beside this DLL (RML's config calls do not find plugin
//     files), and the log goes there too;
//   - the hooks are installed in TsmPluginStart, like every other plugin RML hosts;
//   - safe defaults with no ini: inject (hook = 2), no customhouse hook (survivors owns
//     that tick), no price table in the log (RML's logger mishandles width specifiers);
//   - H->provide is optional;
//   - spacerace.ini beside this DLL switches it: [general] new_goods = 0 adds nothing, so
//     saves stay the base game's (without a spacerace.ini it always runs). Then only
//     ResourceGet is hooked, to read the six goods a save may still name as their vanilla
//     stand-ins (spacerace_data/launches.ini "standin" lines): the save loads, and the next
//     save is a base-game one. Without that, a warehouse slot of an unknown good is left
//     empty and the save writer crashes on it (tested 2026-09-30).
// tools/port_resources.py regenerates this file from the vendored one.

'''
rep('#include "../../src/tesmio_plugin.h"', '#include "../../../vendor/TesmioLoader/src/tesmio_plugin.h"')
rep('static int    g_resHook = 1;', 'static int    g_resHook = 2;')
rep('static int        g_priceReport = 1;', 'static int        g_priceReport = 0;')
rep('static int   g_customsHook    = 1;', 'static int   g_customsHook    = 0;')
rep('''    _snprintf_s(path, sizeof(path), _TRUNCATE, "%s\\\\plugins\\\\resources.ini", g_baseDir);''',
    '''    _snprintf_s(path, sizeof(path), _TRUNCATE, "%s\\\\resources.ini", g_baseDir);''')

# config readers against the file beside the DLL
rep('''extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void)''',
    '''static char g_selfDir[MAX_PATH];
static char g_iniFile[MAX_PATH];

static int CfgInt(const char*, const char* sec, const char* key, int def)
{
    return (int)GetPrivateProfileIntA(sec, key, def, g_iniFile);
}

static int CfgString(const char*, const char* sec, const char* key, char* out, int n, const char* def)
{
    return (int)GetPrivateProfileStringA(sec, key, def, out, (DWORD)n, g_iniFile);
}

extern "C" __declspec(dllexport) unsigned TsmPluginApiVersion(void)''')
s = s.replace('H->configInt(ini, ', 'CfgInt(ini, ').replace('H->configString(ini, ', 'CfgString(ini, ')
rep('''    TsmBind(host);
    info->name    = "resources";
    info->version = "1.7";
''', '''    TsmBind(host);
    info->name    = "resources";
    info->version = "1.7-rml";
    return 0;
}

extern "C" __declspec(dllexport) int TsmPluginStart(void)
{
    HMODULE self = NULL;
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCSTR)&TsmPluginStart, &self) && GetModuleFileNameA(self, g_selfDir, MAX_PATH))
    {
        char* slash = strrchr(g_selfDir, '\\\\');
        if (slash) *slash = 0;
    }
    g_baseDir = g_selfDir;                      // the ini and the log live beside the DLL
    _snprintf_s(g_iniFile, sizeof g_iniFile, _TRUNCATE, "%s\\\\resources.ini", g_selfDir);

    // the Space Race's switch for its new goods. Off: nothing is added, so saves stay the base
    // game's, and a save that still names them reads each as its stand-in
    char spacerace[MAX_PATH];
    _snprintf_s(spacerace, sizeof spacerace, _TRUNCATE, "%s\\\\spacerace.ini", g_selfDir);
    bool aliasOnly = GetFileAttributesA(spacerace) != INVALID_FILE_ATTRIBUTES && GetPrivateProfileIntA("general", "new_goods", 0, spacerace) == 0;
    if (aliasOnly && !LoadAliases(g_selfDir))
    {
        Logf("resource  spacerace.ini new_goods = 0 - no mod resources, saves stay the base game's");
        return 0;
    }
''')
rep('''    if (!g_resHook)
    {
        Logf("resource  hook = 0 - no mod resources");
        return 1;
    }
''', '''    if (aliasOnly) g_resHook = 1;               // observe and alias: no registry, no records of our own
    if (!g_resHook)
    {
        Logf("resource  hook = 0 - no mod resources");
        return 1;
    }
''')
rep('''    if (!InstallInlineHook(g_exeBase + g_resRva, (void*)h_ResourceGet,
                           (void**)&o_ResourceGet, kResourceGetPrologue,
                           STOLEN_BYTES, "ResourceGet"))
        return 1;
''', '''    if (!InstallInlineHook(g_exeBase + g_resRva, (void*)h_ResourceGet,
                           (void**)&o_ResourceGet, kResourceGetPrologue,
                           STOLEN_BYTES, "ResourceGet"))
        return 1;
    if (aliasOnly)
    {
        Logf("resource  spacerace.ini new_goods = 0 - no mod resources, saves stay the base game's; "
             "%d new goods a save may still hold are read as their stand-ins", g_aliasCount);
        return 0;
    }
''')
# the alias table and its lookup, ahead of the hook that uses them
rep('''static unsigned __int64 h_ResourceGet(void* a1, void* a2, void* a3, void* a4)
{''', '''// Space Race stand-ins (new_goods = 0): a new good a save still names is answered with the
// record of the vanilla good that plays it, so warehouses, vehicles and customhouses keep a real
// resource in every slot and the next save writes the stand-in's name.
struct Alias { char name[32]; char as[32]; };
static Alias g_alias[16];
static int   g_aliasCount;
static volatile LONG g_nAliased;

static int LoadAliases(const char* dir)
{
    char path[MAX_PATH];
    _snprintf_s(path, sizeof(path), _TRUNCATE, "%s\\\\spacerace_data\\\\launches.ini", dir);
    FILE* f = NULL;
    if (fopen_s(&f, path, "r") != 0 || !f) return 0;
    char line[256];
    while (fgets(line, sizeof(line), f) && g_aliasCount < 16)
    {
        char k[16] = { 0 }, a[32] = { 0 }, b[32] = { 0 };
        if (sscanf_s(line, "%15s %31s %31s", k, (unsigned)sizeof(k), a, (unsigned)sizeof(a), b, (unsigned)sizeof(b)) == 3 &&
            strcmp(k, "standin") == 0)
        {
            strcpy_s(g_alias[g_aliasCount].name, sizeof(g_alias[0].name), a);
            strcpy_s(g_alias[g_aliasCount].as, sizeof(g_alias[0].as), b);
            ++g_aliasCount;
        }
    }
    fclose(f);
    return g_aliasCount;
}

static BYTE* AliasRecord(const char* name)
{
    ResVector* vec = (ResVector*)(g_exeBase + g_vecRva);
    int off = g_nameOff >= 0 ? g_nameOff : 0;
    for (BYTE* r = vec->begin; r && r + RES_STRIDE <= vec->end; r += RES_STRIDE)
        if (strncmp((const char*)r + off, name, 32) == 0) return r;
    return NULL;
}

static unsigned __int64 h_ResourceGet(void* a1, void* a2, void* a3, void* a4)
{''')
rep('''    unsigned __int64 r = o_ResourceGet(a1, a2, a3, a4);

    if (!name) return r;
''', '''    unsigned __int64 r = o_ResourceGet(a1, a2, a3, a4);

    if (!name) return r;

    if (r == 0 && g_aliasCount)
        for (int i = 0; i < g_aliasCount; i++)
        {
            if (strcmp(g_alias[i].name, name) != 0) continue;
            BYTE* rec = NULL;
            __try { rec = AliasRecord(g_alias[i].as); }
            __except (FaultFilter("resources alias", GetExceptionInformation())) { rec = NULL; }
            if (!rec) break;
            if (InterlockedIncrement(&g_nAliased) <= 12)
                Logf("resource  \\"%s\\" read as its stand-in \\"%s\\" (new_goods = 0)", name, g_alias[i].as);
            return (unsigned __int64)rec;
        }
''')
rep('''    H->provide(TSM_SERVICE_RESOURCES, TSM_RESOURCES_VERSION, &kResourceApi);''',
    '''    if (H->provide) H->provide(TSM_SERVICE_RESOURCES, TSM_RESOURCES_VERSION, &kResourceApi);''')
os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'w', encoding='utf-8').write(header + s)
print('wrote', DST, len(s))
