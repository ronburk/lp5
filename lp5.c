/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c $(xslt-config --cflags --libs) -lexslt
 */

#include <libexslt/exslt.h>
#include <libxml/parser.h>
#include <libxslt/transform.h>
#include <libxslt/xsltutils.h>
#include <stdio.h>

static void print_usage(const char *program)
{
    fprintf(stderr, "Usage: %s <stylesheet> [xml-file] [other args...]\n", program);
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
