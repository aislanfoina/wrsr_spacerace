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
//   - H->provide is optional.
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
''')
rep('''    H->provide(TSM_SERVICE_RESOURCES, TSM_RESOURCES_VERSION, &kResourceApi);''',
    '''    if (H->provide) H->provide(TSM_SERVICE_RESOURCES, TSM_RESOURCES_VERSION, &kResourceApi);''')
os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'w', encoding='utf-8').write(header + s)
print('wrote', DST, len(s))
