import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flet/flet.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:xterm/xterm.dart' as qt;

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
  final FocusNode _focusNode = FocusNode();
  DataChannel? _channel;
  StreamSubscription<Uint8List>? _channelSub;

  @override
  void initState() {
    super.initState();
    widget.control.addInvokeMethodListener(_handleMethodCall);
    widget.control.triggerEvent("mount", "");

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

      if (_channelSub != null && _channel != null) {
        _channel!.send(Uint8List.fromList(utf8.encode(processed)));
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
      final ch = FletBackend.of(context).openDataChannel();
      _channel = ch;
      _channelSub = ch.messages.listen((bytes) {
        if (mounted) {
          _terminal.write(utf8.decode(bytes, allowMalformed: true));
        }
      });

      widget.control.triggerEvent("data_channel_open", {
        "channel_name": "pty",
        "channel_id": ch.id,
      });
    } catch (e) {
      debugPrint("[FletTerminal] Failed to initialize DataChannel in didChangeDependencies: $e");
    }
  }

  Future<dynamic> _handleMethodCall(String name, dynamic args) async {
    if (name == "write") {
      if (mounted) {
        _terminal.write(args["data"] ?? "");
      }
    } else if (name == "clear") {
      if (mounted) {
        _terminal.buffer.clearScrollback();
        _terminal.buffer.clear();
      }
    } else if (name == "focus") {
      _focusNode.requestFocus();
    } else if (name == "clear_selection") {
      _terminalController.clearSelection();
    } else if (name == "select_all") {
      if (mounted) {
        _terminalController.setSelection(
          _terminal.buffer.createAnchor(
            0,
            _terminal.buffer.height - _terminal.viewHeight,
          ),
          _terminal.buffer.createAnchor(
            _terminal.viewWidth,
            _terminal.buffer.height - 1,
          ),
          mode: qt.SelectionMode.line,
        );
      }
    } else if (name == "search") {
      final query = args["query"] as String?;
      final start = (args["start"] as int? ?? 0);
      if (query != null && query.isNotEmpty && mounted) {
        final fullText = _terminal.buffer.getText();
        final lower = fullText.toLowerCase();
        final needle = query.toLowerCase();

        // Count every occurrence (not just the first).
        int count = 0;
        int from = 0;
        while (from != -1) {
          from = lower.indexOf(needle, from);
          if (from != -1) {
            count++;
            from += needle.length;
          }
        }

        // Find the next match at or after `start` (wraps to first).
        int index = lower.indexOf(needle, start);
        if (index == -1) index = lower.indexOf(needle);
        if (index != -1) {
          // Map the string offset to grid (col,row) so we can select the
          // matched run. xterm has no find engine, so we surface the match by
          // selecting it (visible highlight via the `selection` theme color).
          final before = fullText.substring(0, index);
          final startRow = before.split('\n').length - 1;
          final startCol = before.length - before.lastIndexOf('\n') - 1;
          final endRow = fullText.substring(0, index + query.length).split('\n').length - 1;
          final endCol = (index + query.length) -
              fullText.substring(0, index + query.length).lastIndexOf('\n') - 1;

          _terminalController.setSelection(
            _terminal.buffer.createAnchor(startCol, startRow),
            _terminal.buffer.createAnchor(endCol, endRow),
            mode: qt.SelectionMode.line,
          );
          widget.control.triggerEvent(
            "selection_change",
            jsonEncode({
              "query": query,
              "found": true,
              "count": count,
              "index": index,
            }),
          );
        } else {
          widget.control.triggerEvent(
            "selection_change",
            jsonEncode({
              "query": query,
              "found": false,
              "count": 0,
              "index": -1,
            }),
          );
        }
      }
    }
    return null;
  }

  qt.TerminalTheme _parseTheme(Map<dynamic, dynamic>? themeProps) {
    const d = qt.TerminalThemes.defaultTheme;
    if (themeProps == null) return d;

    Color parseColor(String key, Color fallback) {
      if (themeProps.containsKey(key)) {
        final val = themeProps[key];
        if (val is String) {
          final clean = val.replaceFirst('#', '').replaceFirst('0x', '');
          final hex = int.tryParse(clean, radix: 16);
          if (hex != null) {
            if (clean.length == 6) {
              if (key == "selection" || key == "searchHitBackground" || key == "searchHitBackgroundCurrent") {
                return Color(hex | 0x66000000);
              }
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

  qt.TerminalCursorType _parseCursorType(String? type) {
    if (type == "underline") return qt.TerminalCursorType.underline;
    if (type == "bar" || type == "verticalBar") return qt.TerminalCursorType.verticalBar;
    return qt.TerminalCursorType.block;
  }

  @override
  Widget build(BuildContext context) {
    final themeMap = widget.control.get<Map>("theme") ?? (widget.control.properties["theme"] as Map?);
    final theme = _parseTheme(themeMap);
    final style = _parseStyle();
    final cursorType = _parseCursorType(widget.control.getString("cursor_style"));
    final cursorBlink = widget.control.getBool("cursor_blink", true)!;
    final autofocus = widget.control.getBool("auto_focus", true)!;
    final readOnly = widget.control.getBool("read_only", false)!;

    final media = MediaQuery.of(context);
    final isMobile = media.size.width < 600;

    Widget termView = qt.TerminalView(
      _terminal,
      controller: _terminalController,
      focusNode: _focusNode,
      theme: theme,
      textStyle: style,
      autofocus: autofocus,
      readOnly: readOnly,
      cursorType: cursorType,
      alwaysShowCursor: cursorBlink,
      deleteDetection: isMobile,
      keyboardType: TextInputType.text,
    );

    termView = GestureDetector(
      onSecondaryTapUp: (details) async {
        if (_terminalController.selection != null) {
          final selectedText = _terminal.buffer.getText(_terminalController.selection!);
          if (selectedText.isNotEmpty) {
            await Clipboard.setData(ClipboardData(text: selectedText));
            _terminalController.clearSelection();
            widget.control.triggerEvent("copy", selectedText);
            return;
          }
        }
        final data = await Clipboard.getData(Clipboard.kTextPlain);
        if (data != null && data.text != null && data.text!.isNotEmpty) {
          if (_channel != null) {
            _channel!.send(utf8.encode(data.text!));
          } else {
            widget.control.triggerEvent("data", data.text!);
          }
        }
      },
      child: termView,
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
    _channel?.close();
    _focusNode.dispose();
    _terminalController.dispose();
    super.dispose();
  }
}
