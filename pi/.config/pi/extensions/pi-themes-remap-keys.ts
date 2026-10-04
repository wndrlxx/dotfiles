import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import piThemes from "../npm/node_modules/pi-themes/index.ts";

/** Keep pi-themes commands and lifecycle hooks, but cycle with Shift+Cmd+T.
 * The package's own extension is disabled in settings.json; themes still load.
 * Wrapping the installed factory avoids patches that npm updates would overwrite.
 */
export default function (pi: ExtensionAPI) {
  const remappedShortcuts = new Proxy(pi, {
    get(target, property, receiver) {
      if (property === "registerShortcut") {
        return (key: Parameters<ExtensionAPI["registerShortcut"]>[0], shortcut: Parameters<ExtensionAPI["registerShortcut"]>[1]) =>
          target.registerShortcut(key === "ctrl+shift+t" ? "shift+super+t" : key, shortcut);
      }
      if (property === "registerCommand") {
        return (name: string, command: Parameters<ExtensionAPI["registerCommand"]>[1]) =>
          target.registerCommand(name, {
            ...command,
            description: command.description?.replace("Ctrl+Shift+T", "Shift+Cmd+T"),
          });
      }
      return Reflect.get(target, property, receiver);
    },
  });
  return piThemes(remappedShortcuts);
}
