import type { ExtensionContext } from "@earendil-works/pi-coding-agent";

type TuiModule = typeof import("@earendil-works/pi-tui");
type Factory = Parameters<ExtensionContext["ui"]["custom"]>[0];
type Tui = Parameters<Factory>[0];
type Theme = Parameters<Factory>[1];
type Bindings = Parameters<Factory>[2];

// Dependency injection keeps rendering tests independent of Pi's module loader.
export function createProblemView(
  lib: TuiModule, tui: Tui, theme: Theme, bindings: Bindings,
  done: (continued: boolean) => void, title: string, body: string, action: string, cancel: string,
) {
  const text = new lib.Text(body, 0, 0);
  const scroll = new lib.ScrollView(text, { scrollbar: "hidden", overscroll: "contain" });
  let height = 1;
  let closed = false;
  const finish = (value: boolean) => { if (!closed) { closed = true; done(value); } };
  const keys = (name: "tui.select.confirm" | "tui.select.cancel") => bindings.getKeys(name).join("/");
  return {
    render(width: number) {
      const w = Math.max(1, Math.floor(width));
      const confirmKey = keys("tui.select.confirm"), cancelKey = keys("tui.select.cancel");
      const navigation = action === cancel ? `${confirmKey}/${cancelKey}: ${action}` :
        `${confirmKey}: ${action} · ${cancelKey}: ${cancel}`;
      const navigationLines = new lib.Text(navigation, 0, 0).render(w);
      const available = Math.max(1, tui.terminal.rows - 5);
      // Physically tiny terminals cannot fit body plus controls; ask for resize
      // rather than presenting a clipped action as if it were the full help.
      if (w < 12 || navigationLines.length + 2 > available) {
        return [lib.truncateToWidth("Resize terminal", w),
          ...new lib.Text(`${confirmKey}/${cancelKey}`, 0, 0).render(w)].slice(0, available);
      }
      const showScrollHint = available >= navigationLines.length + 3;
      height = Math.max(1, Math.min(16, available - 1 - navigationLines.length - Number(showScrollHint)));
      const lines = text.render(w);
      scroll.updateLayout(lines.length, height, () => tui.requestRender());
      const visible = lines.slice(scroll.scrollTop, scroll.scrollTop + height);
      const scrollHint = `${w < 45 ? "↑/↓ scroll" : "↑/↓ PgUp/PgDn Home/End: scroll"} · ${scroll.scrollTop + 1}-${Math.min(lines.length, scroll.scrollTop + height)}/${lines.length}`;
      return [
        lib.truncateToWidth(theme.fg("accent", title), w),
        ...visible,
        ...navigationLines.map((line) => theme.fg("muted", line)),
        ...(showScrollHint ? [lib.truncateToWidth(theme.fg("muted", scrollHint), w)] : []),
      ];
    },
    handleInput(data: string) {
      if (closed) return;
      if (bindings.matches(data, "tui.select.cancel") || lib.matchesKey(data, lib.Key.ctrl("c"))) { finish(false); return; }
      if (bindings.matches(data, "tui.select.confirm")) { finish(true); return; }
      if (lib.matchesKey(data, lib.Key.up)) scroll.scrollBy(-1);
      else if (lib.matchesKey(data, lib.Key.down)) scroll.scrollBy(1);
      else if (lib.matchesKey(data, lib.Key.pageUp)) scroll.scrollBy(-height);
      else if (lib.matchesKey(data, lib.Key.pageDown)) scroll.scrollBy(height);
      else if (lib.matchesKey(data, lib.Key.home)) scroll.scrollToStart();
      else if (lib.matchesKey(data, lib.Key.end)) scroll.scrollToEnd();
      // No input/editor exists: typing and paste cannot alter the displayed text.
    },
    invalidate() { text.invalidate(); scroll.invalidate(); },
  };
}

export async function showProblemView(
  ctx: Pick<ExtensionContext, "ui" | "mode">,
  title: string, body: string, action: string, cancel: string,
): Promise<boolean> {
  if (ctx.mode !== "tui") {
    return await ctx.ui.editor(`${title} — Enter: ${action}; Esc: ${cancel} (not an upload)`,
      `${body}\n\nViewer only. Enter navigates; it does not upload. Edits are discarded.`) !== undefined;
  }
  const lib = await import("@earendil-works/pi-tui");
  return ctx.ui.custom<boolean>((tui, theme, bindings, done) =>
    createProblemView(lib, tui, theme, bindings, done, title, body, action, cancel));
}
