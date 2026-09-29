/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
 */

#include <libexslt/exslt.h>
#include <libxml/parser.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <stdio.h>
#include <string.h>

typedef int (*command_function)(int argc, char *argv[]);

struct command_entry {
    const char *name;
    command_function function;
};

static int command_foo(int argc, char *argv[])
{
    int i;

    puts("command foo:");
    for (i = 0; i < argc; ++i) {
        printf("  argv[%d]: %s\n", i, argv[i]);
    }
    return 0;
}

static const struct command_entry commands[] = {
    {"foo", command_foo}
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

static command_function find_command(const char *name)
{
    size_t i;

    for (i = 0; i < sizeof(commands) / sizeof(commands[0]); ++i) {
        if (strcmp(commands[i].name, name) == 0) {
            return commands[i].function;
        }
    }
    return NULL;
}

static void print_usage(const char *program)
{
    fprintf(stderr,
        "Usage: %s <command> [args...]\n"
        "       %s <stylesheet.xsl|stylesheet.xslt> [xml-file] [other args...]\n",
        program, program);
}

int main(int argc, char *argv[])
{
    xsltStylesheetPtr stylesheet;
    xmlDocPtr document;
    xmlDocPtr result;
    int status = 0;

    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    if (!is_stylesheet_name(argv[1])) {
        command_function function = find_command(argv[1]);
        if (function == NULL) {
            fprintf(stderr, "lp5: unknown command '%s'\n", argv[1]);
            print_usage(argv[0]);
            return 1;
        }
        return function(argc, argv);
    }

    xmlInitParser();
    exsltRegisterAll();
    stylesheet = xsltParseStylesheetFile((const xmlChar *) argv[1]);
    if (stylesheet == NULL) {
        fprintf(stderr, "lp5: cannot load stylesheet '%s'\n", argv[1]);
        xmlCleanupParser();
        return 1;
    }

    if (argc < 3) {
        xsltFreeStylesheet(stylesheet);
        xsltCleanupGlobals();
        xmlCleanupParser();
        return 0;
    }

    if (argc > 3) {
        fprintf(stderr, "lp5: additional arguments are not supported yet\n");
        print_usage(argv[0]);
        status = 1;
    } else {
        document = xmlReadFile(argv[2], NULL, XML_PARSE_NONET);
        if (document == NULL) {
            fprintf(stderr, "lp5: cannot load XML file '%s'\n", argv[2]);
            status = 1;
        } else {
            result = xsltApplyStylesheet(stylesheet, document, NULL);
            if (result == NULL) {
                fprintf(stderr, "lp5: transformation failed\n");
                status = 1;
            } else {
                if (xsltSaveResultToFile(stdout, result, stylesheet) < 0 ||
                        fflush(stdout) == EOF) {
                    fprintf(stderr, "lp5: could not write transformation result\n");
                    status = 1;
                }
                xmlFreeDoc(result);
            }
            xmlFreeDoc(document);
        }
    }

    xsltFreeStylesheet(stylesheet);
    xsltCleanupGlobals();
    xmlCleanupParser();
    return status;
}
