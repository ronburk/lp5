/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
 */

#include <libexslt/exslt.h>
#include <libxml/parser.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (*command_function)(xsltStylesheetPtr stylesheet, int argc,
    char *argv[]);

const char *LP5Source = "lp5.lp5";
const char *LP5OutputName;
static FILE *LP5OutputFile;

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

static int transform_file(xsltStylesheetPtr stylesheet, const char *filename)
{
    xmlDocPtr document;
    xmlDocPtr result;
    int status = 0;

    document = xmlReadFile(filename, NULL, XML_PARSE_NONET);
    if (document == NULL) {
        fprintf(stderr, "lp5: cannot load XML file '%s'\n", filename);
        return 1;
    }

    result = xsltApplyStylesheet(stylesheet, document, NULL);
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
    char *default_input = NULL;
    int status;

    if (argc > 2) {
        fprintf(stderr, "Usage: lp5 [-s source-dir] weave [xml-file]\n");
        return 1;
    }
    if (argc == 2) {
        input_filename = argv[1];
    } else {
        default_input = weave_default_input();
        if (default_input == NULL) {
            fprintf(stderr, "lp5: out of memory\n");
            return 1;
        }
        input_filename = default_input;
    }

    status = transform_file(stylesheet, input_filename);
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
        status = transform_file(stylesheet, argv[first_argument + 1]);
    }

    xsltFreeStylesheet(stylesheet);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return finish_output(status);
}
