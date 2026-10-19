/* A small MCP-over-stdio front end for the lp5 command line harness. */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *project;
static const char *lp5_program = "./lp5";

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
    char *q0 = quote_arg(lp5_program), *q1 = quote_arg(project);
    char *q2 = quote_arg(command), *q3 = a ? quote_arg(a) : NULL;
    char *q4 = b ? quote_arg(b) : NULL; char line[8192]; FILE *pipe;
    size_t size = 1, used = 0; char *result = malloc(1);
    if (!q0 || !q1 || !q2 || (a && !q3) || (b && !q4) || !result) return NULL;
    snprintf(line, sizeof line, "%s %s %s%s%s%s%s 2>&1", q0, q1, q2,
        q3 ? " " : "", q3 ? q3 : "", q4 ? " " : "", q4 ? q4 : "");
    pipe = popen(line, "r");
    if (!pipe) { free(result); result = NULL; }
    while (pipe && fgets(line, sizeof line, pipe)) {
        size_t n = strlen(line), needed = used + n + 1;
        if (needed > size) { char *grown = realloc(result, needed); if (!grown) { free(result); result = NULL; break; } result = grown; size = needed; }
        if (result) { memcpy(result + used, line, n); used += n; result[used] = 0; }
    }
    if (pipe) pclose(pipe);
    free(q0); free(q1); free(q2); free(q3); free(q4);
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
    response(id, "{\"tools\":[{\"name\":\"check\",\"description\":\"Validate an LP5 article.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"article\":{\"type\":\"string\"}},\"required\":[\"article\"]}},{\"name\":\"show_article\",\"description\":\"Display an LP5 article.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"article\":{\"type\":\"string\"}}}},{\"name\":\"show_bundle\",\"description\":\"Display a code bundle.\",\"inputSchema\":{\"type\":\"object\",\"properties\":{\"name\":{\"type\":\"string\"}}}},{\"name\":\"weave\",\"description\":\"Refresh the project index.\",\"inputSchema\":{\"type\":\"object\"}},{\"name\":\"tangle\",\"description\":\"Generate project output.\",\"inputSchema\":{\"type\":\"object\"}}]}");
}

static void tool_call(const char *id, const char *json)
{
    const char *name_value = json_string(json, "name"); const char *arg;
    char name[64];
    char *output = NULL;
    if (!name_value) { error_response(id, -32602, "tools/call requires a tool name"); return; }
    snprintf(name, sizeof name, "%s", name_value);
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
    if (argc != 2) { fprintf(stderr, "usage: lp5mcp PROJECT\n"); return 2; }
    project = argv[1];
    { const char *configured = getenv("LP5_EXECUTABLE"); if (configured) lp5_program = configured; }
    while (fgets(line, sizeof line, stdin)) {
        const char *id = json_id(line); const char *method = json_string(line, "method");
        if (!method) { error_response(id ? id : "", -32600, "invalid JSON-RPC request"); continue; }
        if (!id) continue;
        if (strcmp(method, "initialize") == 0) response(id, "{\"protocolVersion\":\"2025-03-26\",\"capabilities\":{\"tools\":{}},\"serverInfo\":{\"name\":\"lp5\",\"version\":\"1.0\"}}");
        else if (strcmp(method, "tools/list") == 0) tools_list(id);
        else if (strcmp(method, "tools/call") == 0) tool_call(id, line);
        else error_response(id, -32601, "method not found");
    }
    return 0;
}
