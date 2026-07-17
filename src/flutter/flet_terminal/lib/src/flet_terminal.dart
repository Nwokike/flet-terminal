import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flet/flet.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:xterm/xterm.dart' as qt;
import 'package:xterm/flutter.dart' as qtf;
import 'package:xterm/src/core/buffer/cell_offset.dart';
import 'package:xterm/src/core/buffer/range_line.dart';

class FletTerminalControl extends StatefulWidget {
  final Control control;

  const FletTerminalControl({
    super.key,
    required this.control,
  });

  @override
  State<FletTerminalControl> createState() => _FletTerminalControlState();
}

class _FletTerminalControlState extends State<FletTerminalControl> {
  late final qt.Terminal _terminal;
  final qt.TerminalController _terminalController = qt.TerminalController();
  late final DataChannel _channel;
  StreamSubscription<Uint8List>? _channelSub;

  @override
  void initState() {
    super.initState();
    widget.control.addInvokeMethodListener(_handleMethodCall);

    final maxLines = widget.control.getInt("scrollback", 10000)!;
    _terminal = qt.Terminal(maxLines: maxLines);

    // Setup input forwarding from terminal to Python with sticky modifiers support
    _terminal.onOutput = (String output) {
      bool ctrl = widget.control.getBool("ctrl_active", false)!;
      bool alt = widget.control.getBool("alt_active", false)!;

      String processed = output;
      bool changed = false;

      if (ctrl && processed.length == 1) {
        int code = processed.codeUnitAt(0);
        if (code >= 97 && code <= 122) {
          // a-z
          processed = String.fromCharCode(code - 96);
          changed = true;
        } else if (code >= 65 && code <= 90) {
          // A-Z
          processed = String.fromCharCode(code - 64);
          changed = true;
        }
      }

      if (alt) {
        processed = '\x1b$processed';
        changed = true;
      }

      if (changed) {
        widget.control.updateProperties({
          "ctrl_active": false,
          "alt_active": false,
        }, dart: true, python: true, notify: true);

        widget.control.triggerEvent("modifier_reset", "");
      }

      if (_channelSub != null) {
        _channel.send(Uint8List.fromList(utf8.encode(processed)));
      } else {
        widget.control.triggerEvent("data", processed);
      }
    };

    // Forward terminal window title changes (OSC 0 / OSC 2)
    _terminal.onTitleChange = (String title) {
      widget.control.triggerEvent("title_change", title);
    };

    // Forward terminal bell notifications (\a)
    _terminal.onBell = () {
      widget.control.triggerEvent("bell", "");
    };

    // Setup resize forwarding to Python
    _terminal.onResize = (width, height, pixelWidth, pixelHeight) {
      widget.control.triggerEvent(
          "resize",
          jsonEncode({
            "cols": width,
            "rows": height,
          }));
    };
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_channelSub != null) return; // initialize lazily once per spec

    try {
      _channel = FletBackend.of(context).openDataChannel();
      _channelSub = _channel.messages.listen((bytes) {
        if (mounted) {
          setState(() {
            _terminal.write(utf8.decode(bytes, allowMalformed: true));
          });
        }
      });

      widget.control.triggerEvent("data_channel_open", {
        "channel_name": "pty",
        "channel_id": _channel.id,
      });
    } catch (e) {
      debugPrint("[FletTerminal] Failed to initialize DataChannel in didChangeDependencies: $e");
    }
  }

  Future<dynamic> _handleMethodCall(String name, dynamic args) async {
    if (name == "write") {
      if (mounted) {
        setState(() {
          _terminal.write(args["data"] ?? "");
        });
      }
    } else if (name == "clear") {
      if (mounted) {
        setState(() {
          _terminal.clear();
        });
      }
    } else if (name == "focus") {
      _terminalController.setFocus();
    } else if (name == "clear_selection") {
      _terminalController.clearSelection();
    } else if (name == "select_all") {
      if (mounted) {
        _terminalController.setSelection(
          BufferRangeLine(
            CellOffset(0, 0),
            CellOffset(_terminal.viewWidth, _terminal.buffer.height - 1),
          ),
        );
      }
    } else if (name == "search") {
      final query = args["query"] as String?;
      if (query != null && query.isNotEmpty && mounted) {
        final fullText = _terminal.buffer.getText();
        final index = fullText.toLowerCase().indexOf(query.toLowerCase());
        if (index != -1) {
          widget.control.triggerEvent("selection_change", jsonEncode({"query": query, "found": true, "index": index}));
        } else {
          widget.control.triggerEvent("selection_change", jsonEncode({"query": query, "found": false}));
        }
      }
    }
    return null;
  }

  qt.TerminalTheme _parseTheme(Map<dynamic, dynamic>? themeProps) {
    const d = qtf.TerminalThemes.defaultTheme;
    if (themeProps == null) return d;

    Color parseColor(String key, Color fallback) {
      if (themeProps.containsKey(key)) {
        final val = themeProps[key];
        if (val is String) {
          final clean = val.replaceFirst('#', '').replaceFirst('0x', '');
          final hex = int.tryParse(clean, radix: 16);
          if (hex != null) {
            if (clean.length == 6) {
              return Color(hex | 0xFF000000);
            }
            return Color(hex);
          }
        } else if (val is int) {
          return Color(val);
        }
      }
      return fallback;
    }

    return qt.TerminalTheme(
      cursor: parseColor("cursor", d.cursor),
      selection: parseColor("selection", d.selection),
      foreground: parseColor("foreground", d.foreground),
      background: parseColor("background", d.background),
      black: parseColor("black", d.black),
      white: parseColor("white", d.white),
      red: parseColor("red", d.red),
      green: parseColor("green", d.green),
      yellow: parseColor("yellow", d.yellow),
      blue: parseColor("blue", d.blue),
      magenta: parseColor("magenta", d.magenta),
      cyan: parseColor("cyan", d.cyan),
      brightBlack: parseColor("brightBlack", d.brightBlack),
      brightRed: parseColor("brightRed", d.brightRed),
      brightGreen: parseColor("brightGreen", d.brightGreen),
      brightYellow: parseColor("brightYellow", d.brightYellow),
      brightBlue: parseColor("brightBlue", d.brightBlue),
      brightMagenta: parseColor("brightMagenta", d.brightMagenta),
      brightCyan: parseColor("brightCyan", d.brightCyan),
      brightWhite: parseColor("brightWhite", d.brightWhite),
      searchHitBackground: parseColor("searchHitBackground", d.searchHitBackground),
      searchHitBackgroundCurrent: parseColor("searchHitBackgroundCurrent", d.searchHitBackgroundCurrent),
      searchHitForeground: parseColor("searchHitForeground", d.searchHitForeground),
    );
  }

  qt.TerminalStyle _parseStyle() {
    final fontFamily = widget.control.getString("font_family", "JetBrains Mono")!;
    final fontSize = widget.control.getDouble("font_size", 13.0)!;
    return qt.TerminalStyle(
      fontFamily: fontFamily,
      fontSize: fontSize,
    );
  }

  qtf.TerminalCursorType _parseCursorType(String? type) {
    if (type == "underline") return qtf.TerminalCursorType.underline;
    if (type == "bar" || type == "verticalBar") return qtf.TerminalCursorType.verticalBar;
    return qtf.TerminalCursorType.block;
  }

  @override
  Widget build(BuildContext context) {
    final theme = _parseTheme(widget.control.getMap("theme"));
    final style = _parseStyle();
    final cursorType = _parseCursorType(widget.control.getString("cursor_style"));
    final cursorBlink = widget.control.getBool("cursor_blink", true)!;
    final autofocus = widget.control.getBool("auto_focus", true)!;
    final readOnly = widget.control.getBool("read_only", false)!;

    final media = MediaQuery.of(context);
    final isMobile = media.size.width < 600;

    Widget termView = qtf.TerminalView(
      _terminal,
      controller: _terminalController,
      theme: theme,
      textStyle: style,
      autofocus: autofocus,
      readOnly: readOnly,
      cursorType: cursorType,
      alwaysShowCursor: cursorBlink,
      deleteDetection: isMobile,
      keyboardType: TextInputType.emailAddress,
    );

    return LayoutControl(
      control: widget.control,
      child: RepaintBoundary(
        child: termView,
      ),
    );
  }

  @override
  void dispose() {
    widget.control.removeInvokeMethodListener(_handleMethodCall);
    _channelSub?.cancel();
    _channel.close();
    _terminalController.dispose();
    super.dispose();
  }
}
