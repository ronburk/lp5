/* A small MCP-over-stdio front end for the lp5 command line harness. */
#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 700
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static char *executable_directory;
static char *project_name;
static char *project_working_directory;
static const char *lp5_program;

static void print_json_string(const char *s)
{
    putchar('"');
    for (; *s; ++s) {
        unsigned char c = (unsigned char)*s;
        if (c == '"' || c == '\\') printf("\\%c", c);
        else if (c == '\n') fputs("\\n", stdout);
        else if (c == '\r') fputs("\\r", stdout);
        else if (c == '\t') fputs("\\t", stdout);
        else if (c < 32) printf("\\u%04x", c);
        else putchar(c);
    }
    putchar('"');
}

static const char *json_string(const char *json, const char *key)
{
    static char value[4096];
    char needle[128]; const char *p; size_t n = 0;
    snprintf(needle, sizeof needle, "\"%s\"", key);
    p = strstr(json, needle);
    if (!p) return NULL;
    p = strchr(p + strlen(needle), ':');
    if (!p) return NULL;
    while (*++p == ' ' || *p == '\t') {}
    if (*p != '"') return NULL;
    ++p;
    while (*p && *p != '"' && n + 1 < sizeof value) {
        if (*p == '\\' && p[1]) {
            ++p;
            value[n++] = *p++;
        } else value[n++] = *p++;
    }
    value[n] = 0;
    return *p == '"' ? value : NULL;
}

static const char *json_id(const char *json)
{
    static char value[64]; const char *p = strstr(json, "\"id\""); size_t n = 0;
    if (!p || !(p = strchr(p, ':'))) return NULL;
    while (*++p == ' ' || *p == '\t') {}
    if (*p == '"') {
        const char *start = p;
        do { if (*p == '\\' && p[1]) ++p; ++p; } while (*p && *p != '"');
        if (*p != '"' || (size_t)(p - start + 1) >= sizeof value) return NULL;
        memcpy(value, start, (size_t)(p - start + 1));
        value[p - start + 1] = 0;
        return value;
    }
    while (*p && *p != ',' && *p != '}' && *p != ' ' && *p != '\t' && n + 1 < sizeof value)
        value[n++] = *p++;
    value[n] = 0;
    return n ? value : NULL;
}

/* Quote one argument for the subprocess without involving the shell syntax. */
static char *quote_arg(const char *s)
{
    size_t n = 3, i; char *out, *p;
    for (i = 0; s[i]; ++i) n += s[i] == '\'' ? 4 : 1;
    out = malloc(n); if (!out) return NULL;
    p = out; *p++ = '\'';
    for (i = 0; s[i]; ++i) {
        if (s[i] == '\'') { memcpy(p, "'\\''", 4); p += 4; }
        else *p++ = s[i];
    }
    *p++ = '\''; *p = 0;
    return out;
}

static char *run_command(const char *command, const char *a, const char *b)
{
    char *q0 = quote_arg(lp5_program), *q1 = quote_arg(project_name);
    char *q2 = quote_arg(command), *q3 = a ? quote_arg(a) : NULL;
    char *q4 = b ? quote_arg(b) : NULL; char *qcwd = quote_arg(project_working_directory);
    char line[8192]; FILE *pipe;
    size_t size = 1, used = 0; char *result = malloc(1);
    if (!q0 || !q1 || !q2 || !qcwd || (a && !q3) || (b && !q4) || !result) return NULL;
    snprintf(line, sizeof line, "cd %s && %s %s %s%s%s%s%s 2>&1", qcwd, q0, q1, q2,
        q3 ? " " : "", q3 ? q3 : "", q4 ? " " : "", q4 ? q4 : "");
    pipe = popen(line, "r");
    if (!pipe) { free(result); result = NULL; }
    while (pipe && fgets(line, sizeof line, pipe)) {
        size_t n = strlen(line), needed = used + n + 1;
        if (needed > size) { char *grown = realloc(result, needed); if (!grown) { free(result); result = NULL; break; } result = grown; size = needed; }
        if (result) { memcpy(result + used, line, n); used += n; result[used] = 0; }
    }
    if (pipe) pclose(pipe);
    free(q0); free(q1); free(q2); free(q3); free(q4); free(qcwd);
    return result;
}

static void response(const char *id, const char *result)
{
    fputs("{\"jsonrpc\":\"2.0\",\"id\":", stdout); fputs(id, stdout);
    fputs(",\"result\":", stdout); fputs(result, stdout); fputs("}\n", stdout); fflush(stdout);
}

static void error_response(const char *id, int code, const char *message)
{
    fputs("{\"jsonrpc\":\"2.0\",\"id\":", stdout); fputs(id, stdout);
    printf(",\"error\":{\"code\":%d,\"message\":", code); print_json_string(message); fputs("}}\n", stdout); fflush(stdout);
}

static void tools_list(const char *id)
{
    response(id, "{\"tools\":[{\"name\":\"select_project\",\"description\":\"Select an LP5 project. A relative path is resolved relative to the directory containing the lp5mcp executable; the project directory must be <path>.lp5.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"path\":{\"type\":\"string\",\"description\":\"Project path, relative to the lp5mcp executable or absolute.\"}},\"required\":[\"path\"]}},{\"name\":\"check\",\"description\":\"Validate an LP5 article in the selected project.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"article\":{\"type\":\"string\"}},\"required\":[\"article\"]}},{\"name\":\"show_article\",\"description\":\"Display an article from the selected project.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"article\":{\"type\":\"string\"}}}},{\"name\":\"show_bundle\",\"description\":\"Display a code bundle from the selected project.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\"}}}},{\"name\":\"weave\",\"description\":\"Refresh the selected project index.\",\"inputSchema\":{\"type\":\"object\"}},{\"name\":\"tangle\",\"description\":\"Generate output for the selected project.\",\"inputSchema\":{\"type\":\"object\"}}]}");
}

static char *join_path(const char *left, const char *right)
{
    size_t n = strlen(left) + strlen(right) + 2; char *result = malloc(n);
    if (result) snprintf(result, n, "%s/%s", left, right);
    return result;
}

static int select_project(const char *path, char **message)
{
    char *full = path[0] == '/' ? strdup(path) : join_path(executable_directory, path);
    char *slash; char *root; struct stat info;
    if (!full) return 1;
    slash = strrchr(full, '/');
    if (!slash || slash == full || slash[1] == 0) { free(full); return 1; }
    root = malloc(strlen(full) + 6);
    if (!root) { free(full); return 1; }
    sprintf(root, "%s.lp5", full);
    if (stat(root, &info) != 0 || !S_ISDIR(info.st_mode)) {
        free(root); free(full); *message = strdup("project directory does not exist"); return 1;
    }
    free(project_name); project_name = strdup(slash + 1);
    free(project_working_directory); *slash = 0; project_working_directory = strdup(full);
    free(full); free(root);
    if (!project_name || !project_working_directory) return 1;
    *message = strdup("project selected"); return *message ? 0 : 1;
}

static void tool_call(const char *id, const char *json)
{
    const char *name_value = json_string(json, "name"); const char *arg;
    char name[64];
    char *output = NULL;
    if (!name_value) { error_response(id, -32602, "tools/call requires a tool name"); return; }
    snprintf(name, sizeof name, "%s", name_value);
    if (strcmp(name, "select_project") == 0) {
        char *message = NULL; const char *path = json_string(json, "path");
        if (!path) { error_response(id, -32602, "select_project requires path"); return; }
        if (select_project(path, &message) != 0) { error_response(id, -32000, message ? message : "could not select project"); free(message); return; }
        fputs("{\"jsonrpc\":\"2.0\",\"id\":", stdout); fputs(id, stdout);
        fputs(",\"result\":{\"content\":[{\"type\":\"text\",\"text\":", stdout); print_json_string(message);
        fputs("}],\"isError\":false}}\n", stdout); fflush(stdout); free(message); return;
    }
    if (!project_name) { error_response(id, -32000, "no project is selected; call select_project first"); return; }
    arg = json_string(json, "article");
    if (strcmp(name, "check") == 0) output = run_command("check", arg, NULL);
    else if (strcmp(name, "show_article") == 0) output = run_command("show-article", arg, NULL);
    else if (strcmp(name, "show_bundle") == 0) output = run_command("show-bundle", json_string(json, "name"), NULL);
    else if (strcmp(name, "weave") == 0) output = run_command("weave", NULL, NULL);
    else if (strcmp(name, "tangle") == 0) output = run_command("tangle", NULL, NULL);
    else { error_response(id, -32601, "unknown tool"); return; }
    if (!output) { error_response(id, -32603, "could not run LP5 command"); return; }
    fputs("{\"jsonrpc\":\"2.0\",\"id\":", stdout); fputs(id, stdout);
    fputs(",\"result\":{\"content\":[{\"type\":\"text\",\"text\":", stdout);
    print_json_string(output); fputs("}],\"isError\":false}}\n", stdout); fflush(stdout);
    free(output);
}

int main(int argc, char **argv)
{
    char line[65536];
    char *resolved_executable;
    if (argc != 1) { fprintf(stderr, "usage: lp5mcp\n"); return 2; }
    resolved_executable = realpath(argv[0], NULL);
    if (!resolved_executable) return 2;
    executable_directory = strdup(resolved_executable);
    { char *slash = strrchr(executable_directory, '/'); if (slash) *slash = 0; }
    free(resolved_executable);
    { const char *configured = getenv("LP5_EXECUTABLE");
        lp5_program = configured ? configured : "";
        if (!configured) {
            static char sibling[4096];
            snprintf(sibling, sizeof sibling, "%s/lp5", executable_directory);
            lp5_program = sibling;
        }
    }
    while (fgets(line, sizeof line, stdin)) {
        const char *id = json_id(line); const char *method = json_string(line, "method");
        if (!method) { error_response(id ? id : "", -32600, "invalid JSON-RPC request"); continue; }
        if (!id) continue;
        if (strcmp(method, "initialize") == 0) response(id, "{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{\"tools\":{}},\"serverInfo\":{\"name\":\"lp5\",\"version\":\"1.0\"},\"instructions\":\"No project is selected initially. Call select_project with a relative or absolute project path before using project tools.\"}");
        else if (strcmp(method, "tools/list") == 0) tools_list(id);
        else if (strcmp(method, "tools/call") == 0) tool_call(id, line);
        else error_response(id, -32601, "method not found");
    }
    free(executable_directory); free(project_name); free(project_working_directory);
    return 0;
}
