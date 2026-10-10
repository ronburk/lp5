/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
 */

#ifndef _WIN32
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif
#endif

#include <libexslt/exslt.h>
#include <libxml/parser.h>
#include <libxml/uri.h>
#include <libxml/chvalid.h>
#include <libxml/xpathInternals.h>
#include <libxslt/extensions.h>
#include <libxslt/transform.h>
#include <libxslt/variables.h>
#include <libxslt/xsltutils.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <direct.h>
#include <process.h>
#include <windows.h>
#define LP5_GETCWD _getcwd
#define LP5_GETPID _getpid
#else
#include <unistd.h>
#define LP5_GETCWD getcwd
#define LP5_GETPID getpid
#endif

#ifdef _WIN32
#include <io.h>
#include <sys/stat.h>
#define LP5_ISDIR(mode) (((mode) & _S_IFDIR) != 0)
#define LP5_ISREG(mode) (((mode) & _S_IFMT) == _S_IFREG)
#else
#include <dirent.h>
#include <sys/stat.h>
#define LP5_ISDIR(mode) S_ISDIR(mode)
#define LP5_ISREG(mode) S_ISREG(mode)
#endif

typedef int (*command_function)(xsltStylesheetPtr stylesheet, int argc,
    char *argv[]);

const char *LP5ProjectName;
const char *LP5Source;
const char *LP5RootArticleName;
const char *LP5RootArticlePath;
const char *LP5OutputName;
const char *LP5MapName;
const char *LP5WeaveName;
static FILE *LP5OutputFile;
static char *source_entry_path(const char *directory, const char *filename);
static char *append_suffix(const char *text, const char *suffix);
static int ends_with(const char *text, const char *suffix);

static int ascii_filename_equal(const char *left, const char *right)
{
    while (*left != '\0' && *right != '\0') {
        unsigned char a = (unsigned char) *left++;
        unsigned char b = (unsigned char) *right++;
        if (a >= 'A' && a <= 'Z') a = (unsigned char) (a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z') b = (unsigned char) (b - 'A' + 'a');
        if (a != b) return 0;
    }
    return *left == '\0' && *right == '\0';
}

static int ascii_filename_ends_with(const char *text, const char *suffix)
{
    size_t text_length = strlen(text);
    size_t suffix_length = strlen(suffix);
    return text_length >= suffix_length && ascii_filename_equal(
        text + text_length - suffix_length, suffix);
}

#define LP5_EXTENSION_NAMESPACE "http://example.com/lp5ext"

/* Extension functions return nodes named entry with name and type attributes. */

struct extension_function {
    const char *name;
    void (*register_function)(void);
};

static void register_ls_function(void);
static void register_source_marker_function(void);

static char **LP5MapSources;
static size_t LP5MapSourceCount;
static size_t LP5MapSourceCapacity;

static const struct extension_function extension_functions[] = {
    {"ls", register_ls_function},
    {"source-marker", register_source_marker_function}
};

static void clear_source_map_sources(void)
{
    size_t i;
    for (i = 0; i < LP5MapSourceCount; ++i) {
        free(LP5MapSources[i]);
    }
    free(LP5MapSources);
    LP5MapSources = NULL;
    LP5MapSourceCount = 0;
    LP5MapSourceCapacity = 0;
}

static size_t source_map_source_index(const char *filename)
{
    size_t i;
    for (i = 0; i < LP5MapSourceCount; ++i) {
        if (strcmp(LP5MapSources[i], filename) == 0) {
            return i;
        }
    }
    if (LP5MapSourceCount == LP5MapSourceCapacity) {
        size_t capacity = LP5MapSourceCapacity == 0 ? 8 : LP5MapSourceCapacity * 2;
        char **sources = (char **) realloc(LP5MapSources, capacity * sizeof(*sources));
        if (sources == NULL) {
            return (size_t) -1;
        }
        LP5MapSources = sources;
        LP5MapSourceCapacity = capacity;
    }
    LP5MapSources[LP5MapSourceCount] = (char *) malloc(strlen(filename) + 1);
    if (LP5MapSources[LP5MapSourceCount] == NULL) {
        return (size_t) -1;
    }
    strcpy(LP5MapSources[LP5MapSourceCount], filename);
    return LP5MapSourceCount++;
}

static void extension_ls(xmlXPathParserContextPtr parser, int argument_count)
{
    xmlChar *directory;
    xmlNodeSetPtr nodes;
    xmlXPathObjectPtr result;
    size_t path_length;

    if (argument_count != 1) {
        xmlXPathSetArityError(parser);
        return;
    }

    directory = xmlXPathPopString(parser);
    if (directory == NULL) {
        xmlXPathSetTypeError(parser);
        return;
    }

    path_length = strlen((const char *) directory);
    if (path_length == 0) {
        xmlFree(directory);
        xmlXPathSetTypeError(parser);
        return;
    }

    nodes = xmlXPathNodeSetCreate(NULL);
    if (nodes == NULL) {
        xmlFree(directory);
        xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
        return;
    }

#ifdef _WIN32
    {
        struct _finddata_t entry;
        intptr_t search;
        size_t pattern_length = path_length + 3;
        char *pattern = (char *) malloc(pattern_length);
        if (pattern == NULL) {
            xmlXPathFreeNodeSet(nodes);
            xmlFree(directory);
            xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
            return;
        }
        memcpy(pattern, directory, path_length);
        if (path_length != 0 && directory[path_length - 1] != '/' &&
                directory[path_length - 1] != '\\') {
            pattern[path_length++] = '\\';
        }
        pattern[path_length++] = '*';
        pattern[path_length] = '\0';

        search = _findfirst(pattern, &entry);
        free(pattern);
        if (search != -1) {
            do {
                xmlNodePtr node = xmlNewNode(NULL, BAD_CAST "entry");
                if (node == NULL || xmlSetProp(node, BAD_CAST "name",
                        BAD_CAST entry.name) == NULL ||
                        xmlSetProp(node, BAD_CAST "type",
                            BAD_CAST ((entry.attrib & _A_SUBDIR) ? "directory" : "file")) == NULL ||
                        xmlXPathNodeSetAdd(nodes, node) < 0) {
                    if (node != NULL) {
                        xmlFreeNode(node);
                    }
                    _findclose(search);
                    xmlXPathFreeNodeSet(nodes);
                    xmlFree(directory);
                    xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
                    return;
                }
            } while (_findnext(search, &entry) == 0);
            _findclose(search);
        }
    }
#else
    {
        DIR *directory_stream = opendir((const char *) directory);
        struct dirent *entry;

        if (directory_stream == NULL) {
            xmlXPathFreeNodeSet(nodes);
            xmlFree(directory);
            xmlXPathSetError(parser, XPATH_INVALID_OPERAND);
            return;
        }
        while ((entry = readdir(directory_stream)) != NULL) {
            size_t name_length = strlen(entry->d_name);
            size_t full_length = path_length + name_length + 2;
            char *full_path;
            struct stat info;
            xmlNodePtr node;

            if (strcmp(entry->d_name, ".") == 0 ||
                    strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            full_path = (char *) malloc(full_length);
            if (full_path == NULL) {
                closedir(directory_stream);
                xmlXPathFreeNodeSet(nodes);
                xmlFree(directory);
                xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
                return;
            }
            memcpy(full_path, directory, path_length);
            {
                size_t full_path_length = path_length;
                if (full_path_length != 0 && directory[full_path_length - 1] != '/') {
                    full_path[full_path_length++] = '/';
                }
                memcpy(full_path + full_path_length, entry->d_name, name_length + 1);
            }
            if (stat(full_path, &info) != 0) {
                free(full_path);
                continue;
            }
            free(full_path);

            node = xmlNewNode(NULL, BAD_CAST "entry");
            if (node == NULL || xmlSetProp(node, BAD_CAST "name",
                    BAD_CAST entry->d_name) == NULL ||
                    xmlSetProp(node, BAD_CAST "type",
                        BAD_CAST (LP5_ISDIR(info.st_mode) ? "directory" : "file")) == NULL ||
                    xmlXPathNodeSetAdd(nodes, node) < 0) {
                if (node != NULL) {
                    xmlFreeNode(node);
                }
                closedir(directory_stream);
                xmlXPathFreeNodeSet(nodes);
                xmlFree(directory);
                xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
                return;
            }
        }
        closedir(directory_stream);
    }
#endif

    xmlFree(directory);
    result = xmlXPathWrapNodeSet(nodes);
    if (result == NULL) {
        xmlXPathFreeNodeSet(nodes);
        xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
        return;
    }
    valuePush(parser, result);
}

static void register_ls_function(void)
{
    (void) xsltRegisterExtModuleFunction(BAD_CAST "ls",
        BAD_CAST LP5_EXTENSION_NAMESPACE, extension_ls);
}

static void extension_source_marker(xmlXPathParserContextPtr parser,
        int argument_count)
{
    xmlChar *filename;
    xmlChar *marker_name;
    xmlNodePtr context_node;
    xmlNodePtr marker;
    xmlXPathObjectPtr result;
    size_t source_index;
    long line_number;
    char marker_data[64];

    if (argument_count != 2) {
        xmlXPathSetArityError(parser);
        return;
    }
    marker_name = xmlXPathPopString(parser);
    filename = xmlXPathPopString(parser);
    if (filename == NULL || marker_name == NULL) {
        if (filename != NULL) xmlFree(filename);
        if (marker_name != NULL) xmlFree(marker_name);
        xmlXPathSetTypeError(parser);
        return;
    }
    context_node = parser->context->node;
    if (context_node == NULL || context_node->doc == NULL) {
        xmlFree(filename);
        xmlFree(marker_name);
        xmlXPathSetTypeError(parser);
        return;
    }
    source_index = source_map_source_index((const char *) filename);
    if (source_index == (size_t) -1) {
        xmlFree(filename);
        xmlFree(marker_name);
        xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
        return;
    }
    line_number = xmlGetLineNo(context_node);
    if (line_number < 1) {
        line_number = 1;
    }
    snprintf(marker_data, sizeof(marker_data), "%lu %ld",
        (unsigned long) source_index, line_number);
    marker = xmlNewDocPI(context_node->doc, marker_name,
        BAD_CAST marker_data);
    xmlFree(filename);
    xmlFree(marker_name);
    if (marker == NULL) {
        xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
        return;
    }
    result = xmlXPathNewNodeSet(marker);
    if (result == NULL) {
        xmlFreeNode(marker);
        xmlXPathSetError(parser, XPATH_MEMORY_ERROR);
        return;
    }
    valuePush(parser, result);
}

static void register_source_marker_function(void)
{
    (void) xsltRegisterExtModuleFunction(BAD_CAST "source-marker",
        BAD_CAST LP5_EXTENSION_NAMESPACE, extension_source_marker);
}

static void register_extension_functions(void)
{
    size_t i;

    for (i = 0; i < sizeof(extension_functions) / sizeof(extension_functions[0]); ++i) {
        extension_functions[i].register_function();
    }
}

struct command_entry {
    const char *name;
    command_function function;
};

static FILE *output_stream(void)
{
    return LP5OutputFile == NULL ? stdout : LP5OutputFile;
}

static int open_output_file(void)
{
    if (LP5OutputName == NULL || LP5OutputFile != NULL) {
        return 0;
    }

    LP5OutputFile = fopen(LP5OutputName, "wb");
    if (LP5OutputFile == NULL) {
        fprintf(stderr, "lp5: cannot open output file '%s'\n", LP5OutputName);
        return 1;
    }
    return 0;
}

static int finish_output(int status)
{
    if (fflush(output_stream()) == EOF) {
        fprintf(stderr, "lp5: could not write output\n");
        status = 1;
    }
    if (LP5OutputFile != NULL) {
        if (fclose(LP5OutputFile) == EOF) {
            fprintf(stderr, "lp5: could not close output file '%s'\n", LP5OutputName);
            status = 1;
        }
        LP5OutputFile = NULL;
    }
    return status;
}

struct xslt_parameter {
    const char *name;
    const char *value;
};

static char *input_directory(const char *filename)
{
    const char *slash = strrchr(filename, '/');
    const char *backslash = strrchr(filename, '\\');
    const char *separator = slash;
    size_t length;
    char *directory;

    if (separator == NULL || (backslash != NULL && backslash > separator)) {
        separator = backslash;
    }
    if (separator == NULL) {
        directory = (char *) malloc(2);
        if (directory != NULL) {
            memcpy(directory, ".", 2);
        }
        return directory;
    }
    length = (size_t) (separator - filename);
    /* Keep the separator for POSIX root paths and Windows drive roots. */
    if (length == 0 || (length == 2 && filename[1] == ':')) {
        ++length;
    }
    directory = (char *) malloc(length + 1);
    if (directory == NULL) {
        return NULL;
    }
    memcpy(directory, filename, length);
    directory[length] = '\0';
    return directory;
}

struct source_map_position {
    unsigned long generated_line;
    unsigned long generated_column;
    unsigned long source_index;
    unsigned long original_line;
    unsigned long original_column;
};

struct source_map_positions {
    struct source_map_position *items;
    size_t count;
    size_t capacity;
    unsigned long line_count;
};

static int add_source_map_position(struct source_map_positions *positions,
        unsigned long generated_line, unsigned long generated_column,
        unsigned long source_index, unsigned long original_line,
        unsigned long original_column)
{
    struct source_map_position *position;

    if (positions->count > 0) {
        position = &positions->items[positions->count - 1];
        if (position->generated_line == generated_line &&
                position->generated_column == generated_column) {
            position->source_index = source_index;
            position->original_line = original_line;
            position->original_column = original_column;
            return 0;
        }
    }
    if (positions->count == positions->capacity) {
        size_t capacity = positions->capacity == 0 ? 64 : positions->capacity * 2;
        struct source_map_position *items = (struct source_map_position *)
            realloc(positions->items, capacity * sizeof(*items));
        if (items == NULL) {
            return 1;
        }
        positions->items = items;
        positions->capacity = capacity;
    }
    position = &positions->items[positions->count++];
    position->generated_line = generated_line;
    position->generated_column = generated_column;
    position->source_index = source_index;
    position->original_line = original_line;
    position->original_column = original_column;
    return 0;
}

static unsigned long decode_utf8(const unsigned char *text, size_t remaining,
        size_t *byte_count)
{
    unsigned char first = text[0];
    size_t count;
    unsigned long codepoint;
    size_t i;

    if (first < 0x80) {
        *byte_count = 1;
        return first;
    }
    if ((first & 0xe0) == 0xc0) {
        count = 2;
        codepoint = first & 0x1f;
    } else if ((first & 0xf0) == 0xe0) {
        count = 3;
        codepoint = first & 0x0f;
    } else if ((first & 0xf8) == 0xf0) {
        count = 4;
        codepoint = first & 0x07;
    } else {
        *byte_count = 1;
        return 0xfffd;
    }
    if (count > remaining) {
        *byte_count = 1;
        return 0xfffd;
    }
    for (i = 1; i < count; ++i) {
        if ((text[i] & 0xc0) != 0x80) {
            *byte_count = 1;
            return 0xfffd;
        }
        codepoint = (codepoint << 6) | (text[i] & 0x3f);
    }
    *byte_count = count;
    return codepoint;
}

static int process_source_map_markers(const xmlChar *serialized, size_t length,
        const char *marker_name,
        xmlChar **clean_output, size_t *clean_length,
        struct source_map_positions *positions)
{
    size_t marker_start_length = strlen(marker_name) + 3;
    char *marker_start = (char *) malloc(marker_start_length + 1);
    size_t input_offset = 0;
    size_t output_offset = 0;
    unsigned long generated_line = 0;
    unsigned long generated_column = 0;
    unsigned long source_index = 0;
    unsigned long original_line = 0;
    unsigned long original_column = 0;
    int have_source = 0;
    int pending_mapping = 0;
    xmlChar *output = (xmlChar *) malloc(length + 1);

    if (marker_start == NULL || output == NULL) {
        free(marker_start);
        free(output);
        return 1;
    }
    snprintf(marker_start, marker_start_length + 1, "<?%s ", marker_name);
    while (input_offset < length) {
        if (length - input_offset >= marker_start_length &&
                memcmp(serialized + input_offset, marker_start,
                    marker_start_length) == 0) {
            const xmlChar *close = (const xmlChar *) strchr(
                (const char *) serialized + input_offset, '>');
            unsigned long marker_source;
            unsigned long marker_line;
            char *end;
            const char *payload = (const char *) serialized + input_offset +
                marker_start_length;

            if (close == NULL || sscanf(payload, "%lu %lu", &marker_source,
                    &marker_line) != 2 || marker_source >= LP5MapSourceCount) {
                free(output);
                free(marker_start);
                return 1;
            }
            end = (char *) close + 1;
            input_offset = (size_t) (end - (const char *) serialized);
            source_index = marker_source;
            original_line = marker_line == 0 ? 0 : marker_line - 1;
            original_column = 0;
            have_source = 1;
            pending_mapping = 1;
            continue;
        }

        {
            size_t byte_count;
            unsigned long codepoint = decode_utf8(serialized + input_offset,
                length - input_offset, &byte_count);
            memcpy(output + output_offset, serialized + input_offset, byte_count);
            output_offset += byte_count;
            input_offset += byte_count;

            if (codepoint == '\r' || codepoint == '\n' ||
                    codepoint == 0x2028 || codepoint == 0x2029) {
                if (codepoint == '\r' && input_offset < length &&
                        serialized[input_offset] == '\n') {
                    output[output_offset++] = serialized[input_offset++];
                }
                ++generated_line;
                generated_column = 0;
                ++positions->line_count;
                if (have_source) {
                    ++original_line;
                    original_column = 0;
                    if (!pending_mapping && add_source_map_position(positions,
                            generated_line, generated_column, source_index,
                            original_line, original_column) != 0) {
                        free(output);
                        free(marker_start);
                        return 1;
                    }
                }
            } else {
                if (pending_mapping) {
                    if (add_source_map_position(positions, generated_line,
                            generated_column, source_index, original_line,
                            original_column) != 0) {
                        free(output);
                        free(marker_start);
                        return 1;
                    }
                    pending_mapping = 0;
                }
                generated_column += codepoint > 0xffff ? 2 : 1;
                if (have_source) {
                    original_column += codepoint > 0xffff ? 2 : 1;
                }
            }
        }
    }
    output[output_offset] = '\0';
    free(marker_start);
    *clean_output = output;
    *clean_length = output_offset;
    return 0;
}

static int write_json_string(FILE *file, const char *text)
{
    const unsigned char *cursor = (const unsigned char *) text;
    if (fputc('"', file) == EOF) {
        return 1;
    }
    while (*cursor != '\0') {
        switch (*cursor) {
        case '"':
        case '\\':
            if (fputc('\\', file) == EOF || fputc(*cursor, file) == EOF) {
                return 1;
            }
            break;
        case '\b': if (fputs("\\b", file) == EOF) return 1; break;
        case '\f': if (fputs("\\f", file) == EOF) return 1; break;
        case '\n': if (fputs("\\n", file) == EOF) return 1; break;
        case '\r': if (fputs("\\r", file) == EOF) return 1; break;
        case '\t': if (fputs("\\t", file) == EOF) return 1; break;
        default:
            if (*cursor < 0x20) {
                if (fprintf(file, "\\u%04x", *cursor) < 0) {
                    return 1;
                }
            } else if (fputc(*cursor, file) == EOF) {
                return 1;
            }
            break;
        }
        ++cursor;
    }
    return fputc('"', file) == EOF;
}

static char *working_directory_uri(void)
{
    size_t capacity = 256;
    char *directory = NULL;
    char *uri;
    size_t directory_length;
    size_t prefix_length;
    size_t output = 0;
    size_t i;

    while (capacity <= INT_MAX) {
        directory = (char *) malloc(capacity);
        if (directory == NULL) {
            return NULL;
        }
        if (LP5_GETCWD(directory, (int) capacity) != NULL) {
            break;
        }
        free(directory);
        directory = NULL;
        if (errno != ERANGE) {
            return NULL;
        }
        capacity *= 2;
    }
    if (directory == NULL) {
        return NULL;
    }

    directory_length = strlen(directory);
    prefix_length = directory[0] == '/' ? strlen("file://") : strlen("file:///");
    uri = (char *) malloc(prefix_length + directory_length * 3 + 2);
    if (uri == NULL) {
        free(directory);
        return NULL;
    }
    memcpy(uri, directory[0] == '/' ? "file://" : "file:///", prefix_length);
    output = prefix_length;
    for (i = 0; i < directory_length; ++i) {
        unsigned char ch = (unsigned char) directory[i];
        if (ch == '\\') {
            ch = '/';
        }
        if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
                (ch >= '0' && ch <= '9') || ch == '-' || ch == '.' ||
                ch == '_' || ch == '~' || ch == '/' || ch == ':') {
            uri[output++] = (char) ch;
        } else {
            static const char hex[] = "0123456789ABCDEF";
            uri[output++] = '%';
            uri[output++] = hex[ch >> 4];
            uri[output++] = hex[ch & 15];
        }
    }
    if (output == 0 || uri[output - 1] != '/') {
        uri[output++] = '/';
    }
    uri[output] = '\0';
    free(directory);
    return uri;
}

static int write_vlq(FILE *file, long long value)
{
    static const char base64[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    unsigned long long encoded = value < 0
        ? ((unsigned long long) (-value) << 1) | 1
        : (unsigned long long) value << 1;

    do {
        unsigned int digit = (unsigned int) (encoded & 31);
        encoded >>= 5;
        if (encoded != 0) {
            digit |= 32;
        }
        if (fputc(base64[digit], file) == EOF) {
            return 1;
        }
    } while (encoded != 0);
    return 0;
}

static int write_source_map(const char *filename, const char *generated_file,
        const struct source_map_positions *positions)
{
    FILE *file = fopen(filename, "wb");
    char *source_root = working_directory_uri();
    unsigned long line;
    size_t position_index = 0;
    long long previous_source = 0;
    long long previous_original_line = 0;
    long long previous_original_column = 0;
    int status = 0;

    if (file == NULL) {
        fprintf(stderr, "lp5: cannot open source map '%s'\n", filename);
        free(source_root);
        return 1;
    }
    if (source_root == NULL) {
        fclose(file);
        free(source_root);
        fprintf(stderr, "lp5: cannot determine source root for map '%s'\n",
            filename);
        return 1;
    }
    if (fputs("{\"version\":3", file) == EOF) {
        status = 1;
    }
    if (generated_file != NULL && !status) {
        if (fputs(",\"file\":", file) == EOF ||
                write_json_string(file, generated_file) != 0) {
            status = 1;
        }
    }
    if (!status && fputs(",\"sources\":[", file) == EOF) {
        status = 1;
    }
    for (line = 0; line < LP5MapSourceCount && !status; ++line) {
        if (line != 0 && fputc(',', file) == EOF) {
            status = 1;
            break;
        }
        if (write_json_string(file, LP5MapSources[line]) != 0) {
            status = 1;
        }
    }
    if (!status && (fputs("],\"sourceRoot\":", file) == EOF ||
            write_json_string(file, source_root) != 0 ||
            fputs(",\"names\":[],\"mappings\":\"", file) == EOF)) {
        status = 1;
    }
    for (line = 0; line <= positions->line_count && !status; ++line) {
        unsigned long previous_generated_column = 0;
        int first_segment = 1;
        if (line != 0 && fputc(';', file) == EOF) {
            status = 1;
            break;
        }
        while (position_index < positions->count &&
                positions->items[position_index].generated_line == line) {
            const struct source_map_position *position =
                &positions->items[position_index++];
            if (!first_segment && fputc(',', file) == EOF) {
                status = 1;
                break;
            }
            first_segment = 0;
            if (write_vlq(file, (long long) position->generated_column -
                    previous_generated_column) != 0 ||
                    write_vlq(file, (long long) position->source_index -
                    previous_source) != 0 ||
                    write_vlq(file, (long long) position->original_line -
                    previous_original_line) != 0 ||
                    write_vlq(file, (long long) position->original_column -
                    previous_original_column) != 0) {
                status = 1;
                break;
            }
            previous_generated_column = position->generated_column;
            previous_source = position->source_index;
            previous_original_line = position->original_line;
            previous_original_column = position->original_column;
        }
    }
    if (!status && (fputs("\"}\n", file) == EOF || fflush(file) == EOF)) {
        status = 1;
    }
    if (fclose(file) == EOF) {
        status = 1;
    }
    free(source_root);
    if (status) {
        fprintf(stderr, "lp5: could not write source map '%s'\n", filename);
    }
    return status;
}

static int save_result_with_source_map(xmlDocPtr result,
        xsltStylesheetPtr stylesheet, const char *map_filename,
        const char *marker_name)
{
    xmlChar *serialized = NULL;
    xmlChar *clean_output = NULL;
    int serialized_length = 0;
    size_t clean_length = 0;
    struct source_map_positions positions = {NULL, 0, 0, 0};
    int status = 0;

    if (xsltSaveResultToString(&serialized, &serialized_length, result,
            stylesheet) < 0 || serialized == NULL || serialized_length < 0) {
        fprintf(stderr, "lp5: could not serialize tangle output\n");
        status = 1;
    } else if (process_source_map_markers(serialized,
            (size_t) serialized_length, marker_name,
            &clean_output, &clean_length,
            &positions) != 0) {
        fprintf(stderr, "lp5: could not process source map markers\n");
        status = 1;
    } else if (open_output_file() != 0 ||
            fwrite(clean_output, 1, clean_length, output_stream()) != clean_length) {
        fprintf(stderr, "lp5: could not write transformation result\n");
        status = 1;
    } else if (write_source_map(map_filename, LP5OutputName, &positions) != 0) {
        status = 1;
    }

    free(positions.items);
    xmlFree(clean_output);
    xmlFree(serialized);
    return status;
}

static int transform_file(xsltStylesheetPtr stylesheet, const char *filename,
        const struct xslt_parameter *parameters, size_t parameter_count,
        xmlDocPtr document, const char *source_map_filename,
        const char *source_map_marker_name)
{
    xmlDocPtr result;
    xsltTransformContextPtr context;
    int status = 0;

    if (source_map_filename != NULL) {
        clear_source_map_sources();
    }
    if (document == NULL) {
        FILE *input = fopen(filename, "rb");
        if (input == NULL) {
            fprintf(stderr, "lp5: cannot load XML file '%s': %s\n",
                filename, strerror(errno));
            if (source_map_filename != NULL) {
                clear_source_map_sources();
            }
            return 1;
        }
        fclose(input);

        document = xmlReadFile(filename, NULL, XML_PARSE_NONET);
    }
    if (document == NULL) {
        fprintf(stderr, "lp5: cannot parse XML file '%s'\n", filename);
        if (source_map_filename != NULL) {
            clear_source_map_sources();
        }
        return 1;
    }

    context = xsltNewTransformContext(stylesheet, document);
    if (context == NULL) {
        fprintf(stderr, "lp5: cannot create transformation context\n");
        xmlFreeDoc(document);
        if (source_map_filename != NULL) {
            clear_source_map_sources();
        }
        return 1;
    }
    if (parameter_count > 0 && parameters == NULL) {
        fprintf(stderr, "lp5: invalid stylesheet parameters\n");
        xsltFreeTransformContext(context);
        xmlFreeDoc(document);
        if (source_map_filename != NULL) {
            clear_source_map_sources();
        }
        return 1;
    }
    {
        size_t i;
        for (i = 0; i < parameter_count; ++i) {
            if (xsltQuoteOneUserParam(context, BAD_CAST parameters[i].name,
                    BAD_CAST parameters[i].value) != 0) {
                fprintf(stderr, "lp5: cannot set stylesheet parameter '%s'\n",
                    parameters[i].name);
                xsltFreeTransformContext(context);
                xmlFreeDoc(document);
                if (source_map_filename != NULL) {
                    clear_source_map_sources();
                }
                return 1;
            }
        }
    }
    result = xsltApplyStylesheetUser(stylesheet, document, NULL, NULL, NULL,
        context);
    xsltFreeTransformContext(context);
    if (result == NULL) {
        fprintf(stderr, "lp5: transformation failed\n");
        status = 1;
    } else if (source_map_filename != NULL) {
        status = save_result_with_source_map(result, stylesheet,
            source_map_filename, source_map_marker_name);
        xmlFreeDoc(result);
    } else {
        if (open_output_file() != 0 ||
                xsltSaveResultToFile(output_stream(), result, stylesheet) < 0) {
            fprintf(stderr, "lp5: could not write transformation result\n");
            status = 1;
        }
        xmlFreeDoc(result);
    }
    xmlFreeDoc(document);
    if (source_map_filename != NULL) {
        clear_source_map_sources();
    }
    return status;
}

static void usage_tangle(void)
{
    fprintf(stderr,
        "Usage: lp5 <project-name> tangle\n"
        "  Write the unnamed bundle and each angle-bracket output bundle to the project directory.\n");
    exit(1);
}

struct tangle_output {
    char *bundle;
    char *filename;
    char *map_filename;
};

static char *duplicate_string(const char *text)
{
    size_t length = strlen(text);
    char *copy = (char *) malloc(length + 1);
    if (copy != NULL) {
        memcpy(copy, text, length + 1);
    }
    return copy;
}

static int valid_output_basename(const char *name)
{
    const unsigned char *p = (const unsigned char *) name;
    size_t length = strlen(name);
    if (length == 0 || strcmp(name, ".") == 0 || strcmp(name, "..") == 0 ||
            ascii_filename_equal(name, "weave.xml") ||
            ascii_filename_ends_with(name, ".lp5") ||
            name[length - 1] == '.' || name[length - 1] == ' ') {
        return 0;
    }
    for (; *p != '\0'; ++p) {
        if (*p < 32 || strchr("/\\:<>\"|?*", *p) != NULL) {
            return 0;
        }
    }
    return 1;
}

static void free_tangle_outputs(struct tangle_output *outputs, size_t count)
{
    size_t i;
    for (i = 0; i < count; ++i) {
        free(outputs[i].bundle);
        free(outputs[i].filename);
        free(outputs[i].map_filename);
    }
    free(outputs);
}

static xmlNodePtr find_article_record(xmlNodePtr articles, const char *filename)
{
    xmlNodePtr article;
    for (article = articles->children; article != NULL; article = article->next) {
        xmlChar *file;
        xmlNodePtr found;
        if (article->type != XML_ELEMENT_NODE ||
                xmlStrcmp(article->name, BAD_CAST "article") != 0) {
            continue;
        }
        file = xmlGetProp(article, BAD_CAST "file");
        found = file != NULL && strcmp((const char *) file, filename) == 0 ?
            article : NULL;
        xmlFree(file);
        if (found != NULL) return found;
    }
    return NULL;
}

static int article_record_is_rooted(xmlNodePtr articles, const char *filename)
{
    xmlNodePtr article = find_article_record(articles, filename);
    while (article != NULL) {
        xmlChar *file = xmlGetProp(article, BAD_CAST "file");
        xmlChar *parent;
        int is_root = file != NULL &&
            strcmp((const char *) file, LP5RootArticleName) == 0;
        xmlFree(file);
        if (is_root) return 1;
        parent = xmlGetProp(article, BAD_CAST "parent");
        if (parent == NULL) return 0;
        article = find_article_record(articles, (const char *) parent);
        xmlFree(parent);
    }
    return 0;
}

static int bundle_is_rooted(xmlNodePtr articles, xmlNodePtr bundle)
{
    xmlNodePtr section;
    for (section = bundle->children; section != NULL; section = section->next) {
        xmlChar *article;
        int rooted;
        if (section->type != XML_ELEMENT_NODE ||
                xmlStrcmp(section->name, BAD_CAST "section") != 0) {
            continue;
        }
        article = xmlGetProp(section, BAD_CAST "article");
        rooted = article != NULL && article_record_is_rooted(articles,
            (const char *) article);
        xmlFree(article);
        if (rooted) return 1;
    }
    return 0;
}

static int append_tangle_output(struct tangle_output **outputs,
        size_t *count, const char *bundle, const char *basename,
        const char *map_basename)
{
    struct tangle_output *grown;
    char *filename;
    char *map_filename;
    size_t i;

    if (!valid_output_basename(basename) ||
            !valid_output_basename(map_basename)) {
        fprintf(stderr, "lp5: invalid tangle output filename '%s'\n", basename);
        return 1;
    }
    filename = source_entry_path(LP5Source, basename);
    map_filename = source_entry_path(LP5Source, map_basename);
    if (filename == NULL || map_filename == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        free(filename);
        free(map_filename);
        return 1;
    }
    for (i = 0; i < *count; ++i) {
        if (ascii_filename_equal(filename, (*outputs)[i].filename) ||
                ascii_filename_equal(filename, (*outputs)[i].map_filename) ||
                ascii_filename_equal(map_filename, (*outputs)[i].filename) ||
                ascii_filename_equal(map_filename, (*outputs)[i].map_filename)) {
            fprintf(stderr, "lp5: tangle output filename collision at '%s'\n",
                basename);
            free(filename);
            free(map_filename);
            return 1;
        }
    }
    grown = (struct tangle_output *) realloc(*outputs,
        (*count + 1) * sizeof(**outputs));
    if (grown == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        free(filename);
        free(map_filename);
        return 1;
    }
    *outputs = grown;
    grown[*count].bundle = duplicate_string(bundle);
    grown[*count].filename = filename;
    grown[*count].map_filename = map_filename;
    if (grown[*count].bundle == NULL) {
        free(filename);
        free(map_filename);
        return 1;
    }
    ++*count;
    return 0;
}

static int collect_tangle_outputs(struct tangle_output **outputs,
        size_t *count)
{
    xmlDocPtr weave = xmlReadFile(LP5WeaveName, NULL, XML_PARSE_NONET);
    xmlNodePtr root;
    xmlNodePtr articles;
    xmlNodePtr bundle_list;
    xmlNodePtr bundle;
    char *default_name = append_suffix(LP5ProjectName, ".out");
    char *default_map = append_suffix(LP5ProjectName, ".map");
    int status = 0;

    *outputs = NULL;
    *count = 0;
    if (default_name == NULL || default_map == NULL ||
            append_tangle_output(outputs, count, "", default_name,
                default_map) != 0) {
        free(default_name);
        free(default_map);
        xmlFreeDoc(weave);
        return 1;
    }
    free(default_name);
    free(default_map);
    if (weave == NULL || (root = xmlDocGetRootElement(weave)) == NULL ||
            xmlStrcmp(root->name, BAD_CAST "lp5-weave") != 0) {
        fprintf(stderr, "lp5: cannot read current weave index '%s'\n", LP5WeaveName);
        xmlFreeDoc(weave);
        return 1;
    }
    bundle_list = root->children;
    while (bundle_list != NULL &&
            !(bundle_list->type == XML_ELEMENT_NODE &&
              xmlStrcmp(bundle_list->name, BAD_CAST "bundles") == 0)) {
        bundle_list = bundle_list->next;
    }
    if (bundle_list == NULL) {
        fprintf(stderr, "lp5: weave index has no bundle list\n");
        xmlFreeDoc(weave);
        return 1;
    }
    articles = root->children;
    while (articles != NULL &&
            !(articles->type == XML_ELEMENT_NODE &&
              xmlStrcmp(articles->name, BAD_CAST "articles") == 0)) {
        articles = articles->next;
    }
    if (articles == NULL) {
        fprintf(stderr, "lp5: weave index has no article list\n");
        xmlFreeDoc(weave);
        return 1;
    }
    for (bundle = bundle_list->children; bundle != NULL; bundle = bundle->next) {
        xmlChar *name;
        size_t length;
        char *filename;
        char *map_basename;
        if (bundle->type != XML_ELEMENT_NODE ||
                xmlStrcmp(bundle->name, BAD_CAST "bundle") != 0) {
            continue;
        }
        name = xmlGetProp(bundle, BAD_CAST "name");
        if (name == NULL) continue;
        length = strlen((const char *) name);
        if (length < 3 || name[0] != '<' || name[length - 1] != '>') {
            xmlFree(name);
            continue;
        }
        if (!bundle_is_rooted(articles, bundle)) {
            fprintf(stderr,
                "lp5: output bundle '%s' has no definition reachable from the root article\n",
                (const char *) name);
            xmlFree(name);
            status = 1;
            break;
        }
        filename = (char *) malloc(length - 1);
        if (filename == NULL) {
            xmlFree(name);
            status = 1;
            break;
        }
        memcpy(filename, name + 1, length - 2);
        filename[length - 2] = '\0';
        map_basename = append_suffix(filename, ".map");
        if (map_basename == NULL || append_tangle_output(outputs, count,
                (const char *) name, filename, map_basename) != 0) {
            status = 1;
        }
        free(map_basename);
        free(filename);
        xmlFree(name);
        if (status) break;
    }
    xmlFreeDoc(weave);
    return status;
}

static xmlDocPtr read_tangle_root_article(const char *filename)
{
    xmlDocPtr document = xmlReadFile(filename, NULL, XML_PARSE_NONET);
    xmlNodePtr root;

    if (document == NULL) {
        fprintf(stderr,
            "lp5: cannot read tangle input '%s' as an LP5 root article.\n",
            filename);
        usage_tangle();
    }
    root = xmlDocGetRootElement(document);
    if (root == NULL) {
        fprintf(stderr,
            "lp5: tangle input '%s' is not an LP5 root article: "
            "found no document element; expected <template>.\n",
            filename);
        xmlFreeDoc(document);
        usage_tangle();
    }
    if (xmlStrcmp(root->name, BAD_CAST "template") != 0 || root->ns != NULL) {
        if (root->ns != NULL && root->ns->prefix != NULL) {
            fprintf(stderr,
                "lp5: tangle input '%s' is not an LP5 root article: "
                "found <%s:%s>; expected <template>.\n",
                filename, (const char *) root->ns->prefix,
                (const char *) root->name);
        } else if (root->ns != NULL && root->ns->href != NULL) {
            fprintf(stderr,
                "lp5: tangle input '%s' is not an LP5 root article: "
                "found <%s> in namespace '%s'; expected unqualified <template>.\n",
                filename, (const char *) root->name,
                (const char *) root->ns->href);
        } else {
            fprintf(stderr,
                "lp5: tangle input '%s' is not an LP5 root article: "
                "found <%s>; expected <template>. Use -o to name the generated output.\n",
                filename, (const char *) root->name);
        }
        xmlFreeDoc(document);
        usage_tangle();
    }
    return document;
}

static int command_tangle(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    struct tangle_output *outputs = NULL;
    size_t output_count = 0;
    size_t i;
    int status = 0;

    (void) argv;
    if (argc != 1) {
        fprintf(stderr, "lp5: tangle takes no filename arguments.\n");
        usage_tangle();
    }
    if (collect_tangle_outputs(&outputs, &output_count) != 0) {
        free_tangle_outputs(outputs, output_count);
        return 1;
    }
    for (i = 0; i < output_count; ++i) {
        struct xslt_parameter parameters[6];
        xmlDocPtr document;
        char *directory;
        char marker_name[64];
        static unsigned long marker_sequence;
        snprintf(marker_name, sizeof(marker_name), "lp5sm%lx%lx",
            (unsigned long) time(NULL), marker_sequence++);
        document = read_tangle_root_article(LP5RootArticlePath);
        directory = input_directory(LP5RootArticlePath);
        if (directory == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            xmlFreeDoc(document);
            status = 1;
            break;
        }
        parameters[0].name = "root-location";
        parameters[0].value = LP5RootArticlePath;
        parameters[1].name = "source-directory";
        parameters[1].value = directory;
        parameters[2].name = "source-map-enabled";
        parameters[2].value = "true";
        parameters[3].name = "source-map-marker-name";
        parameters[3].value = marker_name;
        parameters[4].name = "root-bundle-enabled";
        parameters[4].value = i == 0 ? "false" : "true";
        parameters[5].name = "root-bundle";
        parameters[5].value = outputs[i].bundle;
        LP5OutputName = outputs[i].filename;
        status = transform_file(stylesheet, LP5RootArticlePath, parameters, 6,
            document, outputs[i].map_filename, marker_name);
        free(directory);
        status = finish_output(status);
        if (status != 0) break;
    }
    free_tangle_outputs(outputs, output_count);
    return status;
}

static int article_file_is_readable(const char *filename)
{
    struct stat file_status;
    FILE *file = fopen(filename, "rb");

    if (file == NULL || stat(filename, &file_status) != 0 ||
            !LP5_ISREG(file_status.st_mode)) {
        if (file != NULL) {
            fclose(file);
        }
        return 0;
    }
    fclose(file);
    return 1;
}

static int has_path_separator(const char *filename)
{
    return strchr(filename, '/') != NULL || strchr(filename, '\\') != NULL;
}

static char *check_lp5_filename(const char *filename)
{
    const char *last_dot = strrchr(filename, '.');
    size_t filename_length = strlen(filename);
    static const char suffix[] = ".lp5";
    int needs_suffix = last_dot == NULL || last_dot[1] == '\0';
    char *result = (char *) malloc(filename_length +
        (needs_suffix ? sizeof(suffix) : 1));

    if (result == NULL) {
        return NULL;
    }
    memcpy(result, filename, filename_length);
    if (needs_suffix) {
        memcpy(result + filename_length, suffix, sizeof(suffix));
    } else {
        result[filename_length] = '\0';
    }
    return result;
}

static char *check_source_path(const char *filename)
{
    size_t directory_length = strlen(LP5Source);
    size_t filename_length = strlen(filename);
    int needs_separator = directory_length > 0 &&
        LP5Source[directory_length - 1] != '/' &&
        LP5Source[directory_length - 1] != '\\';
    char *result = (char *) malloc(directory_length +
        (size_t) needs_separator + filename_length + 1);

    if (result == NULL) {
        return NULL;
    }
    memcpy(result, LP5Source, directory_length);
    if (needs_separator) {
        result[directory_length++] = '/';
    }
    memcpy(result + directory_length, filename, filename_length + 1);
    return result;
}

static int command_check(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    struct xslt_parameter parameter;
    const char *input_filename;
    char *suffixed_filename = NULL;
    char *source_path = NULL;

    if (argc != 2) {
        fprintf(stderr, "Usage: lp5 check <article-file>\n");
        return 1;
    }

    input_filename = argv[1];
    if (!article_file_is_readable(input_filename) &&
            !has_path_separator(input_filename)) {
        suffixed_filename = check_lp5_filename(input_filename);
        if (suffixed_filename == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            return 1;
        }
        if (article_file_is_readable(suffixed_filename)) {
            input_filename = suffixed_filename;
        } else {
            source_path = check_source_path(suffixed_filename);
            if (source_path == NULL) {
                free(suffixed_filename);
                fprintf(stderr, "lp5: out of memory\n");
                return 1;
            }
            if (article_file_is_readable(source_path)) {
                input_filename = source_path;
            }
        }
    }

    parameter.name = "article-location";
    parameter.value = input_filename;
    {
        int status = transform_file(stylesheet, input_filename, &parameter, 1,
            NULL, NULL, NULL);
        free(source_path);
        free(suffixed_filename);
        return status;
    }
}

static int command_weave(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    char *directory;
    int status;

    (void) argv;
    if (argc != 1) {
        fprintf(stderr, "Usage: lp5 <project-name> weave\n");
        return 1;
    }

    directory = input_directory(LP5RootArticlePath);
    if (directory == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    {
        struct xslt_parameter parameters[2];
        parameters[0].name = "source-directory";
        parameters[0].value = directory;
        parameters[1].name = "root-article";
        parameters[1].value = LP5RootArticleName;
        status = transform_file(stylesheet, LP5RootArticlePath, parameters, 2,
            NULL, NULL, NULL);
    }
    free(directory);
    return status;
}

static int ends_with(const char *text, const char *suffix);
static int valid_xml_text(const char *text);
static int valid_article_basename(const char *filename);
static char *article_source_path(const char *filename);
static FILE *create_replacement_file(char **temporary_name);
static char *read_replacement_article(const char *filename, int *length);
static char *temporary_sibling_path(const char *filename, const char *purpose);

static xmlNodePtr article_children_node(xmlDocPtr document)
{
    xmlNodePtr root = xmlDocGetRootElement(document);
    xmlNodePtr node;

    if (root == NULL || !xmlStrEqual(root->name, BAD_CAST "template")) {
        return NULL;
    }
    for (node = root->children; node != NULL; node = node->next) {
        if (node->type == XML_ELEMENT_NODE &&
                xmlStrEqual(node->name, BAD_CAST "children")) {
            return node;
        }
    }
    return NULL;
}

static int article_child_count(xmlNodePtr children)
{
    xmlNodePtr node;
    int count = 0;

    if (children == NULL) {
        return 0;
    }
    for (node = children->children; node != NULL; node = node->next) {
        if (node->type == XML_ELEMENT_NODE &&
                xmlStrEqual(node->name, BAD_CAST "li")) {
            ++count;
        }
    }
    return count;
}

static int article_has_child(xmlNodePtr children, const char *filename)
{
    xmlNodePtr node;

    if (children == NULL) {
        return 0;
    }
    for (node = children->children; node != NULL; node = node->next) {
        xmlChar *id;
        int matches;
        if (node->type != XML_ELEMENT_NODE ||
                !xmlStrEqual(node->name, BAD_CAST "li")) {
            continue;
        }
        id = xmlGetProp(node, BAD_CAST "id");
        matches = id != NULL && strcmp((const char *) id, filename) == 0;
        xmlFree(id);
        if (matches) {
            return 1;
        }
    }
    return 0;
}

static int find_added_article_id(const char *original_parent,
        const char *updated_parent, char **added_id)
{
    xmlDocPtr original = xmlReadFile(original_parent, NULL, XML_PARSE_NONET);
    xmlDocPtr updated = xmlReadFile(updated_parent, NULL, XML_PARSE_NONET);
    xmlNodePtr original_children;
    xmlNodePtr updated_children;
    xmlNodePtr node;
    int additions = 0;
    int status = 1;

    *added_id = NULL;
    if (original == NULL || updated == NULL) {
        fprintf(stderr, "lp5: cannot parse parent article while adding child\n");
        goto done;
    }
    original_children = article_children_node(original);
    updated_children = article_children_node(updated);
    if (xmlDocGetRootElement(original) == NULL ||
            xmlDocGetRootElement(updated) == NULL || updated_children == NULL ||
            article_child_count(updated_children) !=
                article_child_count(original_children) + 1) {
        fprintf(stderr, "lp5: add-article produced an unexpected child list\n");
        goto done;
    }
    for (node = updated_children->children; node != NULL; node = node->next) {
        xmlChar *id;
        if (node->type != XML_ELEMENT_NODE ||
                !xmlStrEqual(node->name, BAD_CAST "li")) {
            continue;
        }
        id = xmlGetProp(node, BAD_CAST "id");
        if (id == NULL || !valid_article_basename((const char *) id)) {
            xmlFree(id);
            fprintf(stderr, "lp5: add-article produced an invalid child filename\n");
            goto done;
        }
        if (!article_has_child(original_children, (const char *) id)) {
            if (*added_id != NULL) {
                xmlFree(id);
                fprintf(stderr, "lp5: add-article produced multiple new child links\n");
                goto done;
            }
            *added_id = (char *) malloc(xmlStrlen(id) + 1);
            if (*added_id == NULL) {
                xmlFree(id);
                fprintf(stderr, "lp5: out of memory\n");
                goto done;
            }
            memcpy(*added_id, id, xmlStrlen(id) + 1);
            ++additions;
        }
        xmlFree(id);
    }
    if (additions != 1 || *added_id == NULL) {
        fprintf(stderr, "lp5: add-article could not identify the new child link\n");
        goto done;
    }
    status = 0;

done:
    if (status != 0) {
        free(*added_id);
        *added_id = NULL;
    }
    xmlFreeDoc(updated);
    xmlFreeDoc(original);
    return status;
}

static int install_new_file(const char *temporary, const char *target)
{
#ifdef _WIN32
    if (!MoveFileExA(temporary, target, MOVEFILE_WRITE_THROUGH)) {
        fprintf(stderr, "lp5: cannot install article '%s': Windows error %lu\n",
            target, (unsigned long) GetLastError());
        return 1;
    }
#else
    if (link(temporary, target) != 0) {
        fprintf(stderr, "lp5: cannot install article '%s': %s\n",
            target, strerror(errno));
        return 1;
    }
    if (remove(temporary) != 0) {
        fprintf(stderr, "lp5: warning: could not remove staging file '%s': %s\n",
            temporary, strerror(errno));
    }
#endif
    return 0;
}

static int command_add_article(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    struct xslt_parameter parameters[4];
    const char *filename = LP5WeaveName;
    const char *saved_output_name = LP5OutputName;
    const char *article_filename;
    char *parent_path = NULL;
    char *new_article_path = NULL;
    char *new_article_id = NULL;
    char *staged_article_path = NULL;
    char *updated_parent_path = NULL;
    char *backup_parent_path = NULL;
    char *article_contents = NULL;
    xmlChar *staged_article_uri = NULL;
    FILE *staged_article = NULL;
    struct stat input_status;
    struct stat parent_status;
    int article_length = 0;
    int status = 1;
    if (argc < 3 || argc > 4) {
        fprintf(stderr,
            "Usage: lp5 <project-name> add-article <parent-id> <article-file> [before-child-id]\n");
        goto done;
    }
    if (!valid_article_basename(argv[1])) {
        fprintf(stderr, "lp5: parent-id must be an article filename\n");
        goto done;
    }

    article_filename = argv[2];
    parent_path = article_source_path(argv[1]);
    if (parent_path == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        goto done;
    }
    if (stat(parent_path, &parent_status) != 0 ||
            !LP5_ISREG(parent_status.st_mode)) {
        fprintf(stderr, "lp5: parent article '%s' is not a regular file\n",
            parent_path);
        goto done;
    }
    article_contents = read_replacement_article(article_filename, &article_length);
    if (article_contents == NULL) {
        goto done;
    }
    staged_article = create_replacement_file(&staged_article_path);
    if (staged_article == NULL) {
        fprintf(stderr, "lp5: cannot stage new article: %s\n", strerror(errno));
        goto done;
    }
    if (fwrite(article_contents, 1, (size_t) article_length, staged_article) !=
            (size_t) article_length) {
        fprintf(stderr, "lp5: cannot write staged article\n");
        goto done;
    }
#ifdef _WIN32
    if (stat(article_filename, &input_status) == 0 &&
            _chmod(staged_article_path,
                input_status.st_mode & (_S_IREAD | _S_IWRITE)) != 0) {
#else
    if (stat(article_filename, &input_status) == 0 &&
            fchmod(fileno(staged_article), input_status.st_mode & 0777) != 0) {
#endif
        fprintf(stderr, "lp5: cannot preserve article file permissions: %s\n",
            strerror(errno));
        goto done;
    }
    if (fclose(staged_article) == EOF) {
        staged_article = NULL;
        fprintf(stderr, "lp5: cannot finish staging new article\n");
        goto done;
    }
    staged_article = NULL;

    updated_parent_path = NULL;
    {
        FILE *updated_parent = create_replacement_file(&updated_parent_path);
        if (updated_parent == NULL) {
            fprintf(stderr, "lp5: cannot stage updated parent: %s\n", strerror(errno));
            goto done;
        }
#ifdef _WIN32
        if (_chmod(updated_parent_path,
                parent_status.st_mode & (_S_IREAD | _S_IWRITE)) != 0) {
#else
        if (fchmod(fileno(updated_parent), parent_status.st_mode & 0777) != 0) {
#endif
            fprintf(stderr, "lp5: cannot preserve parent article permissions: %s\n",
                strerror(errno));
            fclose(updated_parent);
            goto done;
        }
        if (fclose(updated_parent) == EOF) {
            fprintf(stderr, "lp5: cannot finish staging updated parent\n");
            goto done;
        }
    }
    parameters[0].name = "parent_id";
    parameters[0].value = argv[1];
    parameters[1].name = "before_child_id";
    parameters[1].value = argc == 4 ? argv[3] : "";
    parameters[2].name = "articles_dir";
    parameters[2].value = LP5Source;
    {
        char *base_uri = working_directory_uri();
        xmlChar *path_uri = xmlPathToURI(BAD_CAST staged_article_path);
        if (base_uri != NULL && path_uri != NULL) {
            staged_article_uri = xmlBuildURI(path_uri, BAD_CAST base_uri);
        }
        free(base_uri);
        xmlFree(path_uri);
        if (staged_article_uri == NULL) {
            fprintf(stderr, "lp5: cannot resolve staged article path\n");
            goto done;
        }
    }
    parameters[3].name = "article_file";
    parameters[3].value = (const char *) staged_article_uri;
    LP5OutputName = updated_parent_path;
    status = transform_file(stylesheet, filename, parameters, 4,
        NULL, NULL, NULL);
    status = finish_output(status);
    LP5OutputName = saved_output_name;
    if (status != 0 || find_added_article_id(parent_path, updated_parent_path,
            &new_article_id) != 0) {
        status = 1;
        goto done;
    }

    new_article_path = article_source_path(new_article_id);
    backup_parent_path = temporary_sibling_path(parent_path, "backup");
    if (new_article_path == NULL || backup_parent_path == NULL) {
        fprintf(stderr, "lp5: cannot create article installation paths\n");
        status = 1;
        goto done;
    }
    if (install_new_file(staged_article_path, new_article_path) != 0) {
        status = 1;
        goto done;
    }
    staged_article_path[0] = '\0';

    if (rename(parent_path, backup_parent_path) != 0) {
        fprintf(stderr, "lp5: cannot stage parent article '%s': %s\n",
            parent_path, strerror(errno));
        (void) remove(new_article_path);
        status = 1;
        goto done;
    }
    if (rename(updated_parent_path, parent_path) != 0) {
        int saved_errno = errno;
        if (rename(backup_parent_path, parent_path) != 0) {
            fprintf(stderr,
                "lp5: cannot install updated parent or restore original '%s'\n",
                parent_path);
        } else {
            fprintf(stderr, "lp5: cannot install updated parent '%s': %s\n",
                parent_path, strerror(saved_errno));
        }
        if (remove(new_article_path) != 0) {
            fprintf(stderr, "lp5: could not remove staged article '%s': %s\n",
                new_article_path, strerror(errno));
        }
        status = 1;
        goto done;
    }
    if (remove(backup_parent_path) != 0) {
        fprintf(stderr,
            "lp5: warning: added '%s', but could not remove parent backup '%s': %s\n",
            new_article_id, backup_parent_path, strerror(errno));
    }
    fprintf(stderr, "added article: %s\n", new_article_id);
    status = 0;

done:
    LP5OutputName = saved_output_name;
    if (staged_article != NULL) {
        fclose(staged_article);
    }
    if (staged_article_path != NULL && staged_article_path[0] != '\0') {
        (void) remove(staged_article_path);
    }
    if (updated_parent_path != NULL) {
        (void) remove(updated_parent_path);
    }
    free(article_contents);
    xmlFree(staged_article_uri);
    free(backup_parent_path);
    free(updated_parent_path);
    free(staged_article_path);
    free(new_article_id);
    free(new_article_path);
    free(parent_path);
    return status;
}

static int valid_article_basename(const char *filename)
{
    size_t length = strlen(filename);
    return length > 4 && ends_with(filename, ".lp5") &&
        !has_path_separator(filename) && valid_xml_text(filename);
}

static char *article_source_path(const char *filename)
{
    size_t directory_length = strlen(LP5Source);
    int needs_separator = directory_length > 0 &&
        LP5Source[directory_length - 1] != '/' &&
        LP5Source[directory_length - 1] != '\\';
    size_t filename_length = strlen(filename);
    char *path = malloc(directory_length + (size_t) needs_separator +
        filename_length + 1);

    if (path == NULL) {
        return NULL;
    }
    memcpy(path, LP5Source, directory_length);
    if (needs_separator) {
        path[directory_length++] = '/';
    }
    memcpy(path + directory_length, filename, filename_length + 1);
    return path;
}

static int lookup_remove_parent(const char *article_id, char **parent_id)
{
    xmlDocPtr document = xmlReadFile(LP5WeaveName, NULL, XML_PARSE_NONET);
    xmlNodePtr root;
    xmlNodePtr articles = NULL;
    xmlNodePtr target = NULL;
    xmlNodePtr parent = NULL;
    xmlNodePtr node;
    int target_count = 0;
    int parent_count = 0;

    *parent_id = NULL;
    if (document == NULL) {
        fprintf(stderr, "lp5: cannot parse weave file '%s'\n", LP5WeaveName);
        return 1;
    }
    root = xmlDocGetRootElement(document);
    if (root != NULL && xmlStrEqual(root->name, BAD_CAST "lp5-weave")) {
        for (node = root->children; node != NULL; node = node->next) {
            if (node->type == XML_ELEMENT_NODE &&
                    xmlStrEqual(node->name, BAD_CAST "articles")) {
                articles = node;
                break;
            }
        }
    }
    if (articles == NULL) {
        fprintf(stderr, "lp5: weave file '%s' has no article list\n", LP5WeaveName);
        xmlFreeDoc(document);
        return 1;
    }
    for (node = articles->children; node != NULL; node = node->next) {
        xmlChar *filename;
        xmlNodePtr child;
        if (node->type != XML_ELEMENT_NODE ||
                !xmlStrEqual(node->name, BAD_CAST "article")) {
            continue;
        }
        filename = xmlGetProp(node, BAD_CAST "file");
        if (filename != NULL && strcmp((const char *) filename, article_id) == 0) {
            target = node;
            ++target_count;
        }
        xmlFree(filename);
        for (child = node->children; child != NULL; child = child->next) {
            xmlNodePtr link;
            if (child->type != XML_ELEMENT_NODE ||
                    !xmlStrEqual(child->name, BAD_CAST "children")) {
                continue;
            }
            for (link = child->children; link != NULL; link = link->next) {
                xmlChar *child_id;
                if (link->type != XML_ELEMENT_NODE ||
                        !xmlStrEqual(link->name, BAD_CAST "child")) {
                    continue;
                }
                child_id = xmlGetProp(link, BAD_CAST "file");
                if (child_id != NULL && strcmp((const char *) child_id,
                        article_id) == 0) {
                    parent = node;
                    ++parent_count;
                }
                xmlFree(child_id);
            }
        }
    }
    if (target_count != 1) {
        fprintf(stderr, "lp5: article '%s' must exist exactly once in '%s'\n",
            article_id, LP5WeaveName);
        xmlFreeDoc(document);
        return 1;
    }
    /* The weave emits the root article first, before any orphans. */
    for (node = articles->children; node != NULL; node = node->next) {
        if (node->type == XML_ELEMENT_NODE &&
                xmlStrEqual(node->name, BAD_CAST "article")) {
            if (target == node) {
                fprintf(stderr, "lp5: cannot remove the root article '%s'\n", article_id);
                xmlFreeDoc(document);
                return 1;
            }
            break;
        }
    }
    {
        xmlNodePtr child;
        for (child = target->children; child != NULL; child = child->next) {
            xmlNodePtr link;
            if (child->type != XML_ELEMENT_NODE ||
                    !xmlStrEqual(child->name, BAD_CAST "children")) {
                continue;
            }
            for (link = child->children; link != NULL; link = link->next) {
                if (link->type == XML_ELEMENT_NODE &&
                        xmlStrEqual(link->name, BAD_CAST "child")) {
                    fprintf(stderr,
                        "lp5: cannot remove article '%s' because it has children\n",
                        article_id);
                    xmlFreeDoc(document);
                    return 1;
                }
            }
        }
    }
    if (parent_count != 1 || parent == NULL) {
        fprintf(stderr,
            "lp5: article '%s' must have exactly one parent link in '%s'\n",
            article_id, LP5WeaveName);
        xmlFreeDoc(document);
        return 1;
    }
    {
        xmlChar *filename = xmlGetProp(parent, BAD_CAST "file");
        if (filename == NULL || !valid_article_basename((const char *) filename)) {
            fprintf(stderr, "lp5: parent of '%s' must be a .lp5 filename\n", article_id);
            xmlFree(filename);
            xmlFreeDoc(document);
            return 1;
        }
        *parent_id = malloc(xmlStrlen(filename) + 1);
        if (*parent_id != NULL) {
            memcpy(*parent_id, filename, xmlStrlen(filename) + 1);
        }
        xmlFree(filename);
    }
    xmlFreeDoc(document);
    if (*parent_id == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    return 0;
}

static char *temporary_sibling_path(const char *filename, const char *purpose)
{
    static unsigned long sequence;
    size_t length = strlen(filename) + strlen(purpose) + 64;
    char *candidate = malloc(length);
    unsigned int attempt;

    if (candidate == NULL) {
        return NULL;
    }
    for (attempt = 0; attempt < 1000; ++attempt) {
        struct stat file_status;
        ++sequence;
        snprintf(candidate, length, "%s.lp5-%s-%lu-%lu", filename, purpose,
            (unsigned long) LP5_GETPID(), sequence);
        if (stat(candidate, &file_status) != 0 && errno == ENOENT) {
            return candidate;
        }
    }
    free(candidate);
    return NULL;
}

static int command_remove_article(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    struct xslt_parameter parameters[2];
    const char *saved_output_name = LP5OutputName;
    const char *article_id;
    char *parent_id = NULL;
    char *article_path = NULL;
    char *parent_path = NULL;
    char *updated_path = NULL;
    char *backup_path = NULL;
    struct stat file_status;
    int status = 1;

    if (argc != 2 || !valid_article_basename(argv[1])) {
        fprintf(stderr, "Usage: lp5 remove-article <article-id.lp5>\n");
        return 1;
    }
    if (saved_output_name != NULL) {
        fprintf(stderr, "lp5: -o is not valid with remove-article\n");
        return 1;
    }
    article_id = argv[1];
    if (lookup_remove_parent(article_id, &parent_id) != 0) {
        goto done;
    }
    article_path = article_source_path(article_id);
    parent_path = article_source_path(parent_id);
    if (article_path == NULL || parent_path == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        goto done;
    }
    if (stat(article_path, &file_status) != 0) {
        fprintf(stderr, "lp5: cannot access article '%s': %s\n",
            article_path, strerror(errno));
        goto done;
    }
    if (LP5_ISDIR(file_status.st_mode)) {
        fprintf(stderr, "lp5: article '%s' is a directory\n", article_path);
        goto done;
    }
    if (stat(parent_path, &file_status) != 0) {
        fprintf(stderr, "lp5: cannot access parent article '%s': %s\n",
            parent_path, strerror(errno));
        goto done;
    }
    if (LP5_ISDIR(file_status.st_mode)) {
        fprintf(stderr, "lp5: parent article '%s' is a directory\n", parent_path);
        goto done;
    }
    updated_path = temporary_sibling_path(parent_path, "updated");
    backup_path = temporary_sibling_path(parent_path, "backup");
    if (updated_path == NULL || backup_path == NULL) {
        fprintf(stderr, "lp5: cannot create temporary filenames\n");
        goto done;
    }
    parameters[0].name = "article_id";
    parameters[0].value = article_id;
    parameters[1].name = "parent_id";
    parameters[1].value = parent_id;
    LP5OutputName = updated_path;
    status = transform_file(stylesheet, LP5WeaveName, parameters, 2,
        NULL, NULL, NULL);
    status = finish_output(status);
    LP5OutputName = saved_output_name;
    if (status != 0) {
        goto done;
    }

    if (rename(parent_path, backup_path) != 0) {
        fprintf(stderr, "lp5: cannot stage parent article '%s': %s\n",
            parent_path, strerror(errno));
        status = 1;
        goto done;
    }
    if (rename(updated_path, parent_path) != 0) {
        int saved_errno = errno;
        if (rename(backup_path, parent_path) != 0) {
            fprintf(stderr,
                "lp5: cannot install updated parent or restore original '%s'\n",
                parent_path);
        } else {
            fprintf(stderr, "lp5: cannot install updated parent '%s': %s\n",
                parent_path, strerror(saved_errno));
        }
        status = 1;
        goto done;
    }
    if (remove(article_path) != 0) {
        int saved_errno = errno;
        int moved_updated_parent = rename(parent_path, updated_path) == 0;
        int restored_parent = rename(backup_path, parent_path) == 0;
        if (!moved_updated_parent || !restored_parent) {
            fprintf(stderr,
                "lp5: cannot remove article '%s' and could not restore parent '%s'\n",
                article_path, parent_path);
        } else {
            fprintf(stderr, "lp5: cannot remove article '%s': %s\n",
                article_path, strerror(saved_errno));
        }
        status = 1;
        goto done;
    }
    if (remove(backup_path) != 0) {
        fprintf(stderr,
            "lp5: warning: removed article '%s', but could not remove backup '%s': %s\n",
            article_id, backup_path, strerror(errno));
    }
    status = 0;

done:
    LP5OutputName = saved_output_name;
    if (updated_path != NULL) {
        (void) remove(updated_path);
    }
    free(backup_path);
    free(updated_path);
    free(parent_path);
    free(article_path);
    free(parent_id);
    return status;
}

static int command_show_bundle(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    struct xslt_parameter parameter;
    const char *filename = LP5WeaveName;
    const char *code_name = NULL;

    if (argc == 2 && strcmp(argv[1], "--") != 0) {
        code_name = argv[1];
    } else if (argc == 3 && strcmp(argv[1], "--") == 0) {
        code_name = argv[2];
    } else if (argc != 1) {
        fprintf(stderr,
            "Usage: lp5 <project-name> show-bundle [code-name]\n"
            "       Use -- before a code name that starts with a hyphen.\n");
        return 1;
    }

    parameter.name = "code_name";
    parameter.value = code_name;
    return transform_file(stylesheet, filename,
        code_name == NULL ? NULL : &parameter, code_name == NULL ? 0 : 1,
        NULL, NULL, NULL);
}

/* Check strict UTF-8 and XML 1.0 characters before creating text nodes. */
static int valid_xml_text(const char *text)
{
    const unsigned char *p = (const unsigned char *) text;

    while (*p != 0) {
        unsigned int value;
        unsigned int length;
        unsigned int i;

        if (*p < 0x80) {
            value = *p;
            length = 1;
        } else if (*p >= 0xc2 && *p <= 0xdf) {
            value = *p & 0x1f;
            length = 2;
        } else if (*p >= 0xe0 && *p <= 0xef) {
            value = *p & 0x0f;
            length = 3;
        } else if (*p >= 0xf0 && *p <= 0xf4) {
            value = *p & 0x07;
            length = 4;
        } else {
            return 0;
        }
        for (i = 1; i < length; ++i) {
            if (p[i] < 0x80 || p[i] > 0xbf) {
                return 0;
            }
            value = (value << 6) | (p[i] & 0x3f);
        }
        if ((length == 3 && value < 0x800) ||
                (length == 4 && value < 0x10000) || !xmlIsCharQ(value)) {
            return 0;
        }
        p += length;
    }
    return 1;
}

static int valid_article_filename(const char *filename)
{
    size_t length = strlen(filename);
    return valid_xml_text(filename) && !has_path_separator(filename) &&
        length > 4 && strcmp(filename + length - 4, ".lp5") == 0;
}

static int command_search_terms(xsltStylesheetPtr stylesheet, int argc,
        char *argv[], const char *command_name, const char *term_name,
        const char *usage_term_name)
{
    int argument = 1;
    int all = 0;
    int options_ended = 0;
    int i;
    xmlDocPtr input;
    xmlDocPtr weave;
    xmlNodePtr root;
    xmlNodePtr query;
    xmlNodePtr copied_weave;

    while (argument < argc && strcmp(argv[argument], "--") != 0 &&
            strcmp(argv[argument], "--all") == 0) {
        if (all) {
            fprintf(stderr, "lp5: %s: unexpected argument '%s'\n",
                command_name, argv[argument]);
            return 1;
        }
        all = 1;
        ++argument;
    }
    if (argument < argc && strcmp(argv[argument], "--") == 0) {
        options_ended = 1;
        ++argument;
    }
    if (argument == argc) {
        fprintf(stderr,
            "Usage: lp5 %s [--all] [--] %s [%s ...]\n",
            command_name, usage_term_name, usage_term_name);
        return 1;
    }
    for (i = argument; i < argc; ++i) {
        if (!options_ended && argv[i][0] == '-' &&
                (argv[i][1] == '-' || argv[i][1] != '\0')) {
            fprintf(stderr, "lp5: %s: unexpected argument '%s'\n",
                command_name, argv[i]);
            return 1;
        }
        if (!valid_xml_text(argv[i])) {
            fprintf(stderr, "lp5: %s %d is not valid UTF-8/XML 1.0 text\n",
                term_name, i - argument + 1);
            return 1;
        }
        if (argv[i][strspn(argv[i], " \t\r\n")] == '\0') {
            fprintf(stderr, "lp5: %s %d is empty after normalization\n",
                term_name, i - argument + 1);
            return 1;
        }
    }

    input = xmlNewDoc(BAD_CAST "1.0");
    root = xmlNewNode(NULL, BAD_CAST "lp5-search-input");
    if (input == NULL || root == NULL) {
        xmlFreeNode(root);
        xmlFreeDoc(input);
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    xmlDocSetRootElement(input, root);
    if (xmlNewProp(root, BAD_CAST "mode", BAD_CAST (all ? "all" : "any")) == NULL) {
        goto out_of_memory;
    }
    query = xmlNewChild(root, NULL, BAD_CAST "query", NULL);
    if (query == NULL) {
        goto out_of_memory;
    }
    for (i = argument; i < argc; ++i) {
        /* xmlNewTextChild keeps entity-like strings literal, including '&'. */
        if (xmlNewTextChild(query, NULL, BAD_CAST term_name, BAD_CAST argv[i]) == NULL) {
            goto out_of_memory;
        }
    }
    weave = xmlReadFile(LP5WeaveName, NULL, XML_PARSE_NONET);
    if (weave == NULL) {
        fprintf(stderr, "lp5: cannot read '%s' for %s\n",
            LP5WeaveName, command_name);
        xmlFreeDoc(input);
        return 1;
    }
    copied_weave = xmlDocCopyNode(xmlDocGetRootElement(weave), input, 1);
    xmlFreeDoc(weave);
    if (copied_weave == NULL) {
        goto out_of_memory;
    }
    xmlAddChild(root, copied_weave);
    /* transform_file owns and frees the supplied input document. */
    return transform_file(stylesheet, LP5WeaveName, NULL, 0, input, NULL, NULL);

out_of_memory:
    fprintf(stderr, "lp5: out of memory\n");
    xmlFreeDoc(input);
    return 1;
}

static int command_search(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    return command_search_terms(stylesheet, argc, argv, "search", "term", "TEXT");
}

static int command_search_keywords(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    return command_search_terms(stylesheet, argc, argv,
        "search-keywords", "keyword", "KEYWORD");
}

static int command_list_keywords(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    (void) argv;
    if (argc != 1) {
        fprintf(stderr, "Usage: lp5 list-keywords\n");
        return 1;
    }
    return transform_file(stylesheet, LP5WeaveName, NULL, 0, NULL, NULL, NULL);
}

static int command_show_article(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    const char *filename = argc == 1 ? LP5RootArticleName : argv[1];
    struct xslt_parameter parameter;
    char *path;
    int status;

    if (argc > 2 || !valid_article_filename(filename)) {
        fprintf(stderr,
            "Usage: lp5 <project-name> show-article [article-file.lp5]\n");
        return 1;
    }
    path = check_source_path(filename);
    if (path == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    parameter.name = "article-file";
    parameter.value = filename;
    status = transform_file(stylesheet, path, &parameter, 1, NULL, NULL, NULL);
    free(path);
    return status;
}

static char *read_replacement_article(const char *filename, int *length)
{
    FILE *input = fopen(filename, "rb");
    char *contents = NULL;
    long size;
    int error;

    if (input == NULL) {
        goto failed;
    }
    if (fseek(input, 0, SEEK_END) != 0 || (size = ftell(input)) < 0) {
        goto failed;
    }
    if (size > INT_MAX) {
        errno = EFBIG;
        goto failed;
    }
    if (fseek(input, 0, SEEK_SET) != 0) {
        goto failed;
    }
    contents = (char *) malloc((size_t) size + 1);
    if (contents == NULL) {
        errno = ENOMEM;
        goto failed;
    }
    if (fread(contents, 1, (size_t) size, input) != (size_t) size ||
            ferror(input) || fgetc(input) != EOF || ferror(input)) {
        errno = EIO;
        goto failed;
    }
    if (fclose(input) == EOF) {
        input = NULL;
        goto failed;
    }
    contents[size] = '\0';
    *length = (int) size;
    return contents;

failed:
    error = errno;
    if (input != NULL) {
        fclose(input);
    }
    free(contents);
    fprintf(stderr, "lp5: cannot read article '%s': %s\n",
        filename, strerror(error));
    return NULL;
}

static int validate_replacement_article(xsltStylesheetPtr stylesheet,
        const char *filename, const char *contents, int length)
{
    xmlDocPtr document = xmlReadMemory(contents, length, filename, NULL,
        XML_PARSE_NONET);
    xsltTransformContextPtr context;
    xmlDocPtr result = NULL;
    int status = 1;

    if (document == NULL) {
        fprintf(stderr, "lp5: cannot parse replacement article '%s'\n", filename);
        return 1;
    }
    context = xsltNewTransformContext(stylesheet, document);
    if (context != NULL &&
            xsltQuoteOneUserParam(context, BAD_CAST "article-location",
                BAD_CAST filename) == 0) {
        result = xsltApplyStylesheetUser(stylesheet, document, NULL, NULL,
            NULL, context);
        status = result == NULL || context->state != XSLT_STATE_OK;
    }
    if (status) {
        fprintf(stderr, "lp5: cannot validate replacement article '%s'\n",
            filename);
    }
    xmlFreeDoc(result);
    xsltFreeTransformContext(context);
    xmlFreeDoc(document);
    return status;
}

static FILE *create_replacement_file(char **temporary_name)
{
    const char *directory = LP5Source[0] == '\0' ? "." : LP5Source;
    size_t length = strlen(directory) + 64;
    char *name = (char *) malloc(length);
    FILE *file;
    int descriptor = -1;
    unsigned int attempt;

    if (name == NULL) {
        errno = ENOMEM;
        return NULL;
    }
    for (attempt = 0; attempt < 100; ++attempt) {
#ifdef _WIN32
        snprintf(name, length, "%s/.lp5-replace-%lu-%u.tmp", directory,
            (unsigned long) _getpid(), attempt);
        descriptor = _open(name, _O_WRONLY | _O_CREAT | _O_EXCL | _O_BINARY,
            _S_IREAD | _S_IWRITE);
#else
        snprintf(name, length, "%s/.lp5-replace-%lu-%u.tmp", directory,
            (unsigned long) getpid(), attempt);
        descriptor = open(name, O_WRONLY | O_CREAT | O_EXCL, 0600);
#endif
        if (descriptor >= 0 || errno != EEXIST) {
            break;
        }
    }
    if (descriptor < 0) {
        int error = errno;
        free(name);
        errno = error;
        return NULL;
    }
#ifdef _WIN32
    file = _fdopen(descriptor, "wb");
#else
    file = fdopen(descriptor, "wb");
#endif
    if (file == NULL) {
        int error = errno;
#ifdef _WIN32
        _close(descriptor);
#else
        close(descriptor);
#endif
        remove(name);
        free(name);
        errno = error;
        return NULL;
    }
    *temporary_name = name;
    return file;
}

static int command_replace_article(xsltStylesheetPtr stylesheet, int argc,
        char *argv[])
{
    char *target;
    char *contents = NULL;
    char *temporary_name = NULL;
    struct stat target_info;
    FILE *temporary;
    int length;
    int write_error;
    int status = 1;

    if (argc > 1 && strcmp(argv[1], "--") == 0) {
        --argc;
        ++argv;
    }
    if (argc != 3 || !valid_article_filename(argv[1])) {
        fprintf(stderr,
            "Usage: lp5 replace-article <article-id> <article-file>\n");
        return 1;
    }
    target = check_source_path(argv[1]);
    if (target == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
#ifdef _WIN32
    if (stat(target, &target_info) != 0) {
#else
    if (lstat(target, &target_info) != 0) {
#endif
        fprintf(stderr, "lp5: cannot inspect target article '%s': %s\n",
            target, strerror(errno));
        goto done;
    }
    if (!LP5_ISREG(target_info.st_mode)) {
        fprintf(stderr, "lp5: target article '%s' must be a regular file\n",
            target);
        goto done;
    }
    contents = read_replacement_article(argv[2], &length);
    if (contents == NULL ||
            validate_replacement_article(stylesheet, argv[2], contents,
                length) != 0) {
        goto done;
    }
    temporary = create_replacement_file(&temporary_name);
    if (temporary == NULL) {
        fprintf(stderr, "lp5: cannot create replacement beside '%s': %s\n",
            target, strerror(errno));
        goto done;
    }
    write_error = 0;
    if (fwrite(contents, 1, (size_t) length, temporary) != (size_t) length) {
        write_error = errno != 0 ? errno : EIO;
    }
#ifndef _WIN32
    if (!write_error && fchmod(fileno(temporary), target_info.st_mode & 0777) != 0) {
        write_error = errno;
    }
#endif
    if (fclose(temporary) == EOF && write_error == 0) {
        write_error = errno != 0 ? errno : EIO;
    }
    if (write_error) {
        fprintf(stderr, "lp5: cannot finish replacement for '%s': %s\n",
            target, strerror(write_error));
        goto done;
    }
    /* Never truncate or remove the old article before the replacement is ready. */
#ifdef _WIN32
    if (!MoveFileExA(temporary_name, target, MOVEFILE_REPLACE_EXISTING)) {
        fprintf(stderr, "lp5: cannot replace article '%s': Windows error %lu\n",
            target, (unsigned long) GetLastError());
#else
    if (rename(temporary_name, target) != 0) {
        fprintf(stderr, "lp5: cannot replace article '%s': %s\n",
            target, strerror(errno));
#endif
        status = 1;
        goto done;
    }
    status = 0;

done:
    if (temporary_name != NULL) {
        if (status && remove(temporary_name) != 0) {
            fprintf(stderr, "lp5: cannot remove temporary file '%s': %s\n",
                temporary_name, strerror(errno));
        }
        free(temporary_name);
    }
    free(contents);
    free(target);
    return status;
}

static const struct command_entry commands[] = {
    {"tangle", command_tangle},
    {"check", command_check},
    {"weave", command_weave},
    {"add-article", command_add_article},
    {"remove-article", command_remove_article},
    {"show-bundle", command_show_bundle},
    {"search", command_search},
    {"search-keywords", command_search_keywords},
    {"list-keywords", command_list_keywords},
    {"show-article", command_show_article},
    {"replace-article", command_replace_article}
};

static int ends_with(const char *text, const char *suffix)
{
    size_t text_length = strlen(text);
    size_t suffix_length = strlen(suffix);

    return text_length >= suffix_length &&
        strcmp(text + text_length - suffix_length, suffix) == 0;
}

static const struct command_entry *find_command(const char *name)
{
    size_t i;

    for (i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i) {
        if (strcmp(commands[i].name, name) == 0) {
            return &commands[i];
        }
    }
    return NULL;
}

static int run_command(const struct command_entry *command, int argc,
        char *argv[], int command_argument)
{
    size_t name_length = strlen(command->name);
    char *stylesheet_name = malloc(name_length + sizeof(".xsl"));
    xsltStylesheetPtr stylesheet;
    int status;

    if (stylesheet_name == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    memcpy(stylesheet_name, command->name, name_length);
    memcpy(stylesheet_name + name_length, ".xsl", sizeof(".xsl"));

    xmlInitParser();
    exsltRegisterAll();
    register_extension_functions();
    stylesheet = xsltParseStylesheetFile((const xmlChar *) stylesheet_name);
    if (stylesheet == NULL) {
        fprintf(stderr, "lp5: cannot load stylesheet '%s' for command '%s'\n",
            stylesheet_name, command->name);
        free(stylesheet_name);
        xsltCleanupGlobals();
        xmlCleanupParser();
        return 1;
    }

    free(stylesheet_name);
    status = command->function(stylesheet, argc - command_argument,
        argv + command_argument);
    xsltFreeStylesheet(stylesheet);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return status;
}

static int compare_modification_times(const struct stat *left,
        const struct stat *right)
{
    /* Keep POSIX nanosecond fields isolated from the Windows stat fallback. */
#ifdef _WIN32
    if (left->st_mtime < right->st_mtime) return -1;
    if (left->st_mtime > right->st_mtime) return 1;
#else
    if (left->st_mtim.tv_sec < right->st_mtim.tv_sec) return -1;
    if (left->st_mtim.tv_sec > right->st_mtim.tv_sec) return 1;
    if (left->st_mtim.tv_nsec < right->st_mtim.tv_nsec) return -1;
    if (left->st_mtim.tv_nsec > right->st_mtim.tv_nsec) return 1;
#endif
    return 0;
}

/* Directory time catches added/removed files; article times catch edits. */
static char *source_entry_path(const char *directory, const char *filename)
{
    size_t directory_length = strlen(directory);
    size_t filename_length = strlen(filename);
    int needs_separator = directory_length > 0 &&
        directory[directory_length - 1] != '/' &&
        directory[directory_length - 1] != '\\';
    size_t maximum_length = (size_t) -1;
    char *path;

    if (filename_length > maximum_length - (size_t) needs_separator - 1 ||
            directory_length > maximum_length - filename_length -
                (size_t) needs_separator - 1) {
        return NULL;
    }
    path = (char *) malloc(directory_length + (size_t) needs_separator +
        filename_length + 1);
    if (path == NULL) {
        return NULL;
    }
    memcpy(path, directory, directory_length);
    if (needs_separator) {
        path[directory_length++] = '/';
    }
    memcpy(path + directory_length, filename, filename_length + 1);
    return path;
}

static char *append_suffix(const char *text, const char *suffix)
{
    size_t text_length = strlen(text);
    size_t suffix_length = strlen(suffix);
    char *result;

    if (text_length > (size_t) -1 - suffix_length - 1) {
        return NULL;
    }
    result = malloc(text_length + suffix_length + 1);
    if (result == NULL) {
        return NULL;
    }
    memcpy(result, text, text_length);
    memcpy(result + text_length, suffix, suffix_length + 1);
    return result;
}

static int configure_project(const char *name)
{
    if (name == NULL || name[0] == '\0' || strcmp(name, ".") == 0 ||
            strcmp(name, "..") == 0 || strchr(name, '/') != NULL ||
            strchr(name, '\\') != NULL || !valid_xml_text(name)) {
        fprintf(stderr,
            "lp5: project name must be one nonempty, path-free name\n");
        return 1;
    }

    LP5ProjectName = name;
    LP5Source = append_suffix(name, ".lp5");
    LP5RootArticleName = append_suffix(name, ".lp5");
    if (LP5Source != NULL && LP5RootArticleName != NULL) {
        LP5RootArticlePath = source_entry_path(LP5Source,
            LP5RootArticleName);
        LP5WeaveName = source_entry_path(LP5Source, "weave.xml");
        {
            char *map_basename = append_suffix(name, ".map");
            if (map_basename != NULL) {
                LP5MapName = source_entry_path(LP5Source, map_basename);
            }
            free(map_basename);
        }
    }
    if (LP5Source == NULL || LP5RootArticleName == NULL ||
            LP5RootArticlePath == NULL || LP5WeaveName == NULL ||
            LP5MapName == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        return 1;
    }
    return 0;
}

static void free_project_paths(void)
{
    free((void *) LP5Source);
    free((void *) LP5RootArticleName);
    free((void *) LP5RootArticlePath);
    free((void *) LP5MapName);
    free((void *) LP5WeaveName);
}

static int update_latest_article_time(const char *filename,
        struct stat *latest_time)
{
    struct stat article_time;

    if (!ends_with(filename, ".lp5")) {
        return 0;
    }
    {
        char *path = source_entry_path(LP5Source, filename);
        if (path == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            return 1;
        }
        if (stat(path, &article_time) != 0) {
            fprintf(stderr, "lp5: cannot inspect source article '%s': %s\n",
                path, strerror(errno));
            free(path);
            return 1;
        }
        free(path);
    }

    if (!LP5_ISDIR(article_time.st_mode) &&
            compare_modification_times(&article_time, latest_time) > 0) {
        *latest_time = article_time;
    }
    return 0;
}

static int latest_source_time(struct stat *latest_time)
{
    struct stat directory_time;

    if (stat(LP5Source, &directory_time) != 0) {
        fprintf(stderr, "lp5: cannot inspect source directory '%s': %s\n",
            LP5Source, strerror(errno));
        return 1;
    }
    if (!LP5_ISDIR(directory_time.st_mode)) {
        fprintf(stderr, "lp5: source path '%s' is not a directory\n", LP5Source);
        return 1;
    }
    *latest_time = directory_time;

#ifdef _WIN32
    {
        struct _finddata_t entry;
        intptr_t search;
        size_t directory_length = strlen(LP5Source);
        int needs_separator = directory_length > 0 &&
            LP5Source[directory_length - 1] != '/' &&
            LP5Source[directory_length - 1] != '\\';
        char *pattern = (char *) malloc(directory_length +
            (size_t) needs_separator + 2);

        if (pattern == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            return 1;
        }
        memcpy(pattern, LP5Source, directory_length);
        if (needs_separator) {
            pattern[directory_length++] = '\\';
        }
        pattern[directory_length++] = '*';
        pattern[directory_length] = '\0';
        search = _findfirst(pattern, &entry);
        free(pattern);
        if (search == -1) {
            fprintf(stderr, "lp5: cannot scan source directory '%s'\n",
                LP5Source);
            return 1;
        }
        do {
            if (update_latest_article_time(entry.name, latest_time) != 0) {
                _findclose(search);
                return 1;
            }
        } while (_findnext(search, &entry) == 0);
        _findclose(search);
    }
#else
    {
        DIR *directory_stream = opendir(LP5Source);
        struct dirent *entry;

        if (directory_stream == NULL) {
            fprintf(stderr, "lp5: cannot scan source directory '%s': %s\n",
                LP5Source, strerror(errno));
            return 1;
        }
        for (;;) {
            errno = 0;
            entry = readdir(directory_stream);
            if (entry == NULL) {
                if (errno != 0) {
                    fprintf(stderr,
                        "lp5: cannot read source directory '%s': %s\n",
                        LP5Source, strerror(errno));
                    closedir(directory_stream);
                    return 1;
                }
                break;
            }
            if (strcmp(entry->d_name, ".") == 0 ||
                    strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            if (update_latest_article_time(entry->d_name, latest_time) != 0) {
                closedir(directory_stream);
                return 1;
            }
        }
        closedir(directory_stream);
    }
#endif

    if (stat(LP5Source, &directory_time) != 0) {
        fprintf(stderr, "lp5: cannot recheck source directory '%s': %s\n",
            LP5Source, strerror(errno));
        return 1;
    }
    if (compare_modification_times(&directory_time, latest_time) > 0) {
        *latest_time = directory_time;
    }
    return 0;
}

static int weave_is_current(const struct stat *latest_source_time)
{
    struct stat weave_time;

    if (stat(LP5WeaveName, &weave_time) != 0 ||
            LP5_ISDIR(weave_time.st_mode)) {
        return 0;
    }
    return compare_modification_times(latest_source_time, &weave_time) < 0;
}

static int refresh_weave(void)
{
    const struct command_entry *weave_command = find_command("weave");
    const char *saved_output_name = LP5OutputName;
    char *weave_arguments[] = {(char *) "lp5", (char *) LP5ProjectName,
        (char *) "weave", NULL};
    int status;

    if (weave_command == NULL) {
        fprintf(stderr, "lp5: internal error: missing weave command\n");
        return 1;
    }

    LP5OutputName = LP5WeaveName;
    status = run_command(weave_command, 3, weave_arguments, 2);
    status = finish_output(status);
    LP5OutputName = saved_output_name;
    if (status != 0) {
        fprintf(stderr,
            "lp5: could not refresh '%s'; requested command was not run\n",
            LP5WeaveName);
        return 1;
    }
    return 0;
}

static int ensure_weave_current(void)
{
    struct stat latest_time;

    if (latest_source_time(&latest_time) != 0) {
        return 1;
    }
    if (weave_is_current(&latest_time)) {
        return 0;
    }
    return refresh_weave();
}

static void print_usage(const char *program)
{
    fprintf(stderr,
        "Usage: %s <project-name> <command> [arguments...]\n"
        "       Commands: help, tangle, check, weave, add-article, remove-article, replace-article, show-bundle, search, search-keywords, list-keywords, show-article\n"
        "       A project named X uses X.lp5/X.lp5 as its root article.\n"
        "       weave writes X.lp5/weave.xml. tangle writes the unnamed bundle to X.lp5/X.out and X.lp5/X.map.\n"
        "       Code names like <app.js> also write X.lp5/app.js and X.lp5/app.js.map.\n"
        "       Commands: check <article-file>, add-article <parent-id> <article-file> [before-child-id],\n"
        "       replace-article <article-id> <article-file>, remove-article <article-id.lp5>,\n"
        "       show-article [article-file.lp5], show-bundle [code-name], search [--all] [--] TEXT...,\n"
        "       search-keywords [--all] [--] KEYWORD..., list-keywords, weave, tangle.\n"
        "       Use --help or the help command to display this usage.\n",
        program);
}

static int run_main(int argc, char *argv[])
{
    int status = 0;

    if (argc == 2 && (strcmp(argv[1], "--help") == 0 ||
            strcmp(argv[1], "-h") == 0)) {
        print_usage(argv[0]);
        return 0;
    }
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }
    if (strcmp(argv[2], "help") == 0 || strcmp(argv[2], "--help") == 0 ||
            strcmp(argv[2], "-h") == 0) {
        print_usage(argv[0]);
        return 0;
    }

    {
        const struct command_entry *command = find_command(argv[2]);
        if (command == NULL) {
            fprintf(stderr, "lp5: unknown command '%s'\n", argv[2]);
            print_usage(argv[0]);
            return 1;
        }
        if (configure_project(argv[1]) != 0) {
            return 1;
        }
        if (command->function == command_replace_article) {
            /* Replacement must also work with a missing or stale weave. */
            return run_command(command, argc, argv, 2);
        }
        if (command->function == command_weave) {
            LP5OutputName = LP5WeaveName;
        } else if (ensure_weave_current() != 0) {
            return finish_output(1);
        }
        status = run_command(command, argc, argv, 2);
        return finish_output(status);
    }
}

int main(int argc, char *argv[])
{
    int status = run_main(argc, argv);
    free_project_paths();
    return status;
}
