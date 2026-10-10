import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.registerCommand("golf-login", {
    description: "Log in to Agent Golf (not implemented yet)",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /golf-login <key>", "info");
        return;
      }

      // Never echo or persist the supplied key in this command stub.
      ctx.ui.notify("Agent Golf login is not implemented yet. No key was saved.", "info");
    },
  });

  pi.registerCommand("golf-submit", {
    description: "Submit the current session to Agent Golf (not implemented yet)",
    handler: async (args, ctx) => {
      if (!args.trim()) {
        ctx.ui.notify("Usage: /golf-submit <problem>", "info");
        return;
      }

      ctx.ui.notify("Agent Golf submission is not implemented yet. Nothing was uploaded.", "info");
    },
  });
}
