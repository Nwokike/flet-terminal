import 'package:flet/flet.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flet_terminal/src/extension.dart';
import 'package:flet_terminal/src/flet_terminal.dart';

/// Fabricates a wire-level Control the same way Flet's backend would.
Control _control(String type) {
  final backend = FletBackend(
    pageUri: Uri.parse("uri"),
    assetsDir: "",
    extensions: [],
    multiView: false,
  );
  return Control(
    id: 1,
    type: type,
    properties: const {},
    backend: backend,
  );
}

void main() {
  test("createWidget maps 'FletTerminal' to FletTerminalControl", () {
    final widget = Extension().createWidget(null, _control("FletTerminal"));
    expect(widget, isA<FletTerminalControl>());
  });

  test("createWidget returns null for unknown control types", () {
    expect(Extension().createWidget(null, _control("NotATerminal")), isNull);
  });

  test("createService returns null (terminal is widget-only)", () {
    expect(Extension().createService(_control("FletTerminal")), isNull);
  });
}
