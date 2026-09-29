/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
 */

#include <libexslt/exslt.h>
#include <libxml/parser.h>
#include <libxml/xpathInternals.h>
#include <libxslt/extensions.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <libxslt/variables.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <io.h>
#include <sys/stat.h>
#define LP5_ISDIR(mode) (((mode) & _S_IFDIR) != 0)
#else
#include <dirent.h>
#include <sys/stat.h>
#define LP5_ISDIR(mode) S_ISDIR(mode)
#endif

typedef int (*command_function)(xsltStylesheetPtr stylesheet, int argc,
    char *argv[]);

const char *LP5Source = "lp5.lp5";
const char *LP5OutputName;
static FILE *LP5OutputFile;

#define LP5_EXTENSION_NAMESPACE "http://example.com/lp5ext"

/* Extension functions return nodes named entry with name and type attributes. */

struct extension_function {
    const char *name;
    void (*register_function)(void);
};

static void register_ls_function(void);

static const struct extension_function extension_functions[] = {
    {"ls", register_ls_function}
};

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

static int command_stub(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    int i;

    (void) stylesheet;
    if (open_output_file() != 0) {
        return 1;
    }
    fprintf(output_stream(), "command %s:\n", argv[0]);
    fprintf(output_stream(), "LP5Source: %s\n", LP5Source);
    for (i = 0; i < argc; ++i) {
        fprintf(output_stream(), "  argv[%d]: %s\n", i, argv[i]);
    }
    return 0;
}

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

static int transform_file(xsltStylesheetPtr stylesheet, const char *filename,
        const char *directory)
{
    xmlDocPtr document;
    xmlDocPtr result;
    xsltTransformContextPtr context;
    int status = 0;

    document = xmlReadFile(filename, NULL, XML_PARSE_NONET);
    if (document == NULL) {
        fprintf(stderr, "lp5: cannot load XML file '%s'\n", filename);
        return 1;
    }

    context = xsltNewTransformContext(stylesheet, document);
    if (context == NULL || xsltQuoteOneUserParam(context,
            BAD_CAST "source-directory", BAD_CAST directory) != 0) {
        fprintf(stderr, "lp5: cannot initialize weave source directory\n");
        if (context != NULL) {
            xsltFreeTransformContext(context);
        }
        xmlFreeDoc(document);
        return 1;
    }
    result = xsltApplyStylesheetUser(stylesheet, document, NULL, NULL, NULL,
        context);
    xsltFreeTransformContext(context);
    if (result == NULL) {
        fprintf(stderr, "lp5: transformation failed\n");
        status = 1;
    } else {
        if (open_output_file() != 0 ||
                xsltSaveResultToFile(output_stream(), result, stylesheet) < 0) {
            fprintf(stderr, "lp5: could not write transformation result\n");
            status = 1;
        }
        xmlFreeDoc(result);
    }
    xmlFreeDoc(document);
    return status;
}

static char *weave_default_input(void)
{
    static const char filename[] = "lp5.lp5";
    size_t directory_length = strlen(LP5Source);
    int needs_separator = directory_length > 0 &&
        LP5Source[directory_length - 1] != '/' &&
        LP5Source[directory_length - 1] != '\\';
    char *path = malloc(directory_length + (size_t) needs_separator + sizeof(filename));

    if (path == NULL) {
        return NULL;
    }
    memcpy(path, LP5Source, directory_length);
    if (needs_separator) {
        path[directory_length++] = '/';
    }
    memcpy(path + directory_length, filename, sizeof(filename));
    return path;
}

static int command_weave(xsltStylesheetPtr stylesheet, int argc, char *argv[])
{
    const char *input_filename;
    char *directory;
    char *default_input = NULL;
    int first_argument = 1;
    int status;

    while (first_argument < argc) {
        if (strcmp(argv[first_argument], "-o") == 0) {
            if (first_argument + 1 >= argc) {
                fprintf(stderr, "Usage: lp5 [-s source-dir] weave [-o output-file] [xml-file]\n");
                return 1;
            }
            if (LP5OutputName != NULL &&
                    strcmp(LP5OutputName, argv[first_argument + 1]) != 0) {
                fprintf(stderr, "lp5: output file specified more than once\n");
                return 1;
            }
            LP5OutputName = argv[first_argument + 1];
            first_argument += 2;
        } else {
            break;
        }
    }

    if (first_argument + 1 < argc) {
        fprintf(stderr, "Usage: lp5 [-s source-dir] weave [-o output-file] [xml-file]\n");
        return 1;
    }
    if (first_argument < argc) {
        input_filename = argv[first_argument];
    } else {
        default_input = weave_default_input();
        if (default_input == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            return 1;
        }
        input_filename = default_input;
    }

    directory = input_directory(input_filename);
    if (directory == NULL) {
        fprintf(stderr, "lp5: out of memory\n");
        free(default_input);
        return 1;
    }
    status = transform_file(stylesheet, input_filename, directory);
    free(directory);
    free(default_input);
    return status;
}

static const struct command_entry commands[] = {
    {"tangle", command_stub},
    {"weave", command_weave},
    {"add-article", command_stub},
    {"show-bundle", command_stub}
};

static int ends_with(const char *text, const char *suffix)
{
    size_t text_length = strlen(text);
    size_t suffix_length = strlen(suffix);

    return text_length >= suffix_length &&
        strcmp(text + text_length - suffix_length, suffix) == 0;
}

static int is_stylesheet_name(const char *name)
{
    return ends_with(name, ".xsl") || ends_with(name, ".xslt");
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

static void print_usage(const char *program)
{
    fprintf(stderr,
        "Usage: %s [-s source-dir] [-o output-file] <command> [args...]\n"
        "       Commands: tangle, weave, add-article, show-bundle\n"
        "       %s [-s source-dir] [-o output-file] <stylesheet.xsl|stylesheet.xslt> [xml-file] [other args...]\n"
        "       Source directory defaults to lp5.lp5; LP5Source sets the environment default.\n"
        "       -s overrides both; -o writes command output instead of stdout.\n",
        program, program);
}

int main(int argc, char *argv[])
{
    xsltStylesheetPtr stylesheet;
    const char *environment_source;
    int first_argument = 1;
    int status = 0;

    environment_source = getenv("LP5Source");
    if (environment_source != NULL) {
        LP5Source = environment_source;
    }

    while (first_argument < argc) {
        if (strcmp(argv[first_argument], "-s") == 0) {
            if (first_argument + 1 >= argc) {
                print_usage(argv[0]);
                return 1;
            }
            LP5Source = argv[first_argument + 1];
            first_argument += 2;
        } else if (strcmp(argv[first_argument], "-o") == 0) {
            if (first_argument + 1 >= argc) {
                print_usage(argv[0]);
                return 1;
            }
            LP5OutputName = argv[first_argument + 1];
            first_argument += 2;
        } else {
            break;
        }
    }

    if (first_argument >= argc) {
        print_usage(argv[0]);
        return 1;
    }

    if (!is_stylesheet_name(argv[first_argument])) {
        const struct command_entry *command = find_command(argv[first_argument]);
        if (command == NULL) {
            fprintf(stderr, "lp5: unknown command '%s'\n", argv[first_argument]);
            print_usage(argv[0]);
            return 1;
        }
        status = run_command(command, argc, argv, first_argument);
        return finish_output(status);
    }

    xmlInitParser();
    exsltRegisterAll();
    register_extension_functions();
    stylesheet = xsltParseStylesheetFile((const xmlChar *) argv[first_argument]);
    if (stylesheet == NULL) {
        fprintf(stderr, "lp5: cannot load stylesheet '%s'\n", argv[first_argument]);
        xmlCleanupParser();
        return 1;
    }

    if (first_argument + 1 >= argc) {
        xsltFreeStylesheet(stylesheet);
        xsltCleanupGlobals();
        xmlCleanupParser();
        return 0;
    }

    if (first_argument + 2 < argc) {
        fprintf(stderr, "lp5: additional arguments are not supported yet\n");
        print_usage(argv[0]);
        status = 1;
    } else {
        char *directory = input_directory(argv[first_argument + 1]);
        if (directory == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            status = 1;
        } else {
            status = transform_file(stylesheet, argv[first_argument + 1], directory);
            free(directory);
        }
    }

    xsltFreeStylesheet(stylesheet);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return finish_output(status);
}
