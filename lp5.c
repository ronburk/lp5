/*
 * Build with:
 *     gcc -std=c99 -Wall -Wextra -pedantic -o lp5 lp5.c
 */

#include <stdio.h>

int main(int argc, char *argv[])
{
    int i;

    puts("lp5 command line:");
    for (i = 0; i < argc; ++i) {
        printf("  argv[%d]: %s\n", i, argv[i]);
    }

    return 0;
}
