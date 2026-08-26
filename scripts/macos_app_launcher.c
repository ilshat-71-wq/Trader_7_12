#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int main(int argc, char **argv) {
    (void)argc;

    char executable[PATH_MAX];
    if (realpath(argv[0], executable) == NULL) {
        perror("realpath");
        return 1;
    }

    char *macos_dir = strstr(executable, "/Contents/MacOS/");
    if (macos_dir == NULL) {
        fprintf(stderr, "Invalid Trader_7_12 app bundle path: %s\n", executable);
        return 1;
    }

    *macos_dir = '\0';

    char launcher[PATH_MAX];
    int written = snprintf(launcher, sizeof(launcher), "%s/Contents/Resources/launch_trader_7_12.sh", executable);
    if (written < 0 || (size_t)written >= sizeof(launcher)) {
        fprintf(stderr, "Launcher path is too long\n");
        return 1;
    }

    char *const child_argv[] = {"/bin/zsh", launcher, NULL};
    execv("/bin/zsh", child_argv);

    perror("execv");
    return 1;
}
