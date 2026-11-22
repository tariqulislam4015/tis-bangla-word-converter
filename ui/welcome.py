"""Animated developer welcome screen shown at start-up.

* Fades in, the photo's ring slowly rotates, and the name, title, channel and
  links appear one after another (staggered fade-in).
* Closes by itself after ``WELCOME_SECONDS`` — but stays open while the mouse
  is over it, so the links can be clicked; it closes when the mouse leaves
  (or on a click outside the links / Esc).
* Links open in the default browser with a single click.
"""
from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QApplication, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QToolButton, QVBoxLayout, QWidget)

from config import settings as S

from .icons import icon


class WelcomeVoice:
    """Plays the welcome voice (WAV) asynchronously.

    Uses Windows' built-in ``winsound`` (no extra libraries); on other systems
    the voice is silently skipped.
    """

    def __init__(self, path: str):
        self.path = path
        self.duration = 0.0
        try:
            import wave
            with wave.open(path) as w:
                self.duration = w.getnframes() / float(w.getframerate())
        except Exception:
            self.path = ""

    def play(self) -> None:
        if not self.path:
            return
        try:
            import winsound
            winsound.PlaySound(self.path, winsound.SND_FILENAME | winsound.SND_ASYNC
                               | winsound.SND_NODEFAULT)
        except Exception:
            pass

    def stop(self) -> None:
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass

# Generic link icons (not brand logos), drawn in the platform's colour.
LINK_ICONS: dict[str, tuple[str, str]] = {
    "youtube": ('<circle cx="12" cy="12" r="10" fill="{c}"/><path d="M10 8.2v7.6l6.2-3.8z" fill="#fff"/>',
                "#FF3B30"),
    "facebook": ('<circle cx="12" cy="12" r="10" fill="{c}"/><circle cx="9.3" cy="9.6" r="2.3" fill="#fff"/>'
                 '<circle cx="15" cy="10.3" r="1.8" fill="#fff"/>'
                 '<path d="M5.4 16.8c.6-2.4 2.1-3.6 3.9-3.6s3.3 1.2 3.9 3.6zM13.4 16.8c.3-1.8 1.2-2.8 2.6'
                 '-2.8 1.5 0 2.4 1 2.6 2.8z" fill="#fff"/>', "#2D7FF9"),
    "whatsapp": ('<path d="M12 2.5a9.5 9.5 0 0 0-8.2 14.3L2.6 21.5l4.8-1.2A9.5 9.5 0 1 0 12 2.5z" fill="{c}"/>'
                 '<path d="M8.6 7.8c.3-.4.8-.4 1 0l.9 1.9c.1.3 0 .6-.2.8l-.6.6c.6 1.3 1.6 2.3 2.9 2.9l.6-.6'
                 'c.2-.2.5-.3.8-.2l1.9.9c.4.2.4.7 0 1-.8.8-1.9 1.1-3 .7-2.4-.9-4.2-2.7-5.1-5.1-.4-1.1-.1'
                 '-2.2.8-2.9z" fill="#fff"/>', "#22C35E"),
    "github": ('<circle cx="12" cy="12" r="10" fill="{c}"/><path d="M9.5 8.5 6 12l3.5 3.5M14.5 8.5 18 12'
               'l-3.5 3.5" stroke="#fff" stroke-width="1.9" fill="none" stroke-linecap="round" '
               'stroke-linejoin="round"/>', "#6E7B91"),
    # generic briefcase (professional profile), not the LinkedIn logo
    "linkedin": ('<circle cx="12" cy="12" r="10" fill="{c}"/><rect x="6.8" y="9.2" width="10.4" height="7.3" '
                 'rx="1.4" fill="#fff"/><path d="M9.8 9.2V8a1 1 0 0 1 1-1h2.4a1 1 0 0 1 1 1v1.2" stroke="#fff" '
                 'stroke-width="1.5" fill="none"/><path d="M6.8 12.2h10.4" stroke="{c}" stroke-width="1"/>',
                 "#0A66C2"),
}


def link_icon_pixmap(kind: str, size: int = 26) -> QPixmap:
    from PySide6.QtCore import QByteArray
    from PySide6.QtSvg import QSvgRenderer
    body, color = LINK_ICONS[kind]
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{body.replace("{c}", color)}</svg>'
    ratio = 2
    pm = QPixmap(size * ratio, size * ratio)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(p, QRectF(0, 0, size * ratio, size * ratio))
    p.end()
    pm.setDevicePixelRatio(ratio)
    return pm


class Avatar(QWidget):
    """Circular photo with a slowly rotating gradient ring."""

    def __init__(self, photo: QPixmap, size: int = 150, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._photo = photo
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=360.0, duration=6000, loopCount=-1)
        self._anim.valueChanged.connect(self._set_angle)

    def start(self) -> None:
        self._anim.start()

    def _set_angle(self, v) -> None:
        self._angle = float(v)
        self.update()

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        grad = QConicalGradient(r.center(), self._angle)
        for pos, col in ((0.0, "#3B82F6"), (0.35, "#14B8A6"), (0.7, "#93C5FD"), (1.0, "#3B82F6")):
            grad.setColorAt(pos, QColor(col))
        p.setPen(QPen(QBrush(grad), 5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(r)
        inner = r.adjusted(8, 8, -8, -8)
        path = QPainterPath()
        path.addEllipse(inner)
        p.setClipPath(path)
        if not self._photo.isNull():
            pm = self._photo.scaled(int(inner.width()) * 2, int(inner.height()) * 2,
                                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                    Qt.TransformationMode.SmoothTransformation)
            src = QRectF((pm.width() - inner.width() * 2) / 2, (pm.height() - inner.height() * 2) / 2,
                         inner.width() * 2, inner.height() * 2)
            p.drawPixmap(inner, pm, src)
        else:
            p.fillRect(inner, QColor("#253B55"))
        p.end()


class LinkRow(QWidget):
    def __init__(self, kind: str, title: str, url: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 4, 14, 4)
        lay.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(link_icon_pixmap(kind, 24))
        ic.setFixedSize(QSize(26, 26))
        text = QLabel(f'<a href="{url}" style="color:#DCE7F7; text-decoration:none;">{url}</a>')
        text.setOpenExternalLinks(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        text.setCursor(Qt.CursorShape.PointingHandCursor)
        text.setToolTip(f"Open {title}")
        text.setStyleSheet("font-size: 10pt;")
        lay.addWidget(ic)
        lay.addWidget(text, 1)
        self.setObjectName("LinkRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("#LinkRow { border-radius: 10px; } "
                           "#LinkRow:hover { background: rgba(255,255,255,0.08); }")


class WelcomeScreen(QWidget):
    finished = Signal()

    W, H = 520, 640

    def __init__(self, bengali_font: str = "Nirmala UI", seconds: float = S.WELCOME_SECONDS,
                 voice: bool = True):
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(self.W, self.H)
        self.setWindowTitle(S.APP_NAME)
        self.voice = WelcomeVoice(str(S.resource_path(S.WELCOME_VOICE))) if voice else None
        if self.voice is not None and self.voice.duration:
            # stay on screen until the voice has finished
            seconds = max(seconds, self.voice.duration + 0.4)
        self._ms = int(seconds * 1000)
        self._closing = False
        self._done = False
        self._waited = 0
        prof = S.DEVELOPER_PROFILE

        lay = QVBoxLayout(self)
        lay.setContentsMargins(34, 30, 34, 22)
        lay.setSpacing(6)

        top = QHBoxLayout()
        brand = QLabel(f"<b>{S.APP_SHORT}</b>&nbsp;&nbsp;{S.APP_PRODUCT}")
        brand.setStyleSheet("color:#A9B8CC; font-size:9pt; letter-spacing:0.5px;")
        top.addWidget(brand)
        top.addStretch(1)
        skip = QToolButton()
        skip.setIcon(icon("close", "#A9B8CC"))
        skip.setToolTip("Close (Esc)")
        skip.setStyleSheet("QToolButton{border:none;background:transparent;padding:4px;border-radius:6px}"
                           "QToolButton:hover{background:rgba(255,255,255,0.12)}")
        skip.clicked.connect(self.finish)
        top.addWidget(skip)
        lay.addLayout(top)

        self.avatar = Avatar(QPixmap(str(S.resource_path(prof["photo"]))), 156)
        lay.addSpacing(4)
        lay.addWidget(self.avatar, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addSpacing(10)

        name = QLabel(prof["name"])
        name.setFont(QFont(bengali_font, 21, QFont.Weight.Bold))
        name.setStyleSheet("color:#FFFFFF;")
        name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        position = QLabel(f"______{prof['position']}______")
        position.setStyleSheet("color:#5EEAD4; font-size:12pt; font-weight:600; letter-spacing:0.5px;")
        position.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        channel = QLabel(f"YouTube Channel: <b>{prof['channel']}</b>")
        channel.setStyleSheet("color:#C9D6E8; font-size:10.5pt;")
        channel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._staggered = [name, position, channel]
        for w in self._staggered:
            lay.addWidget(w)
        lay.addSpacing(10)
        for kind, title, url in prof["links"]:
            row = LinkRow(kind, title, url)
            lay.addWidget(row)
            self._staggered.append(row)
        lay.addStretch(1)
        hint = QLabel("Hover here to keep this open  ·  click a link to visit")
        hint.setStyleSheet("color:#7D90AA; font-size:8pt;")
        hint.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(hint)
        self._staggered.append(hint)

        self._effects = []
        for w in self._staggered:
            eff = QGraphicsOpacityEffect(w)
            eff.setOpacity(0.0)
            w.setGraphicsEffect(eff)
            self._effects.append(eff)
        self._anims = []
        self.setWindowOpacity(0.0)

    # ------------------------------------------------------------ painting
    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QLinearGradient(QPointF(0, 0), QPointF(0, r.height()))
        g.setColorAt(0.0, QColor("#14243A"))
        g.setColorAt(1.0, QColor("#0E1A2B"))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 22, 22)
        bar = QRectF(r.left() + 22, r.bottom() - 5, r.width() - 44, 3)
        bg = QLinearGradient(bar.topLeft(), bar.topRight())
        bg.setColorAt(0, QColor("#3B82F6"))
        bg.setColorAt(1, QColor("#14B8A6"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(bar, 1.5, 1.5)
        p.end()

    # ------------------------------------------------------------ lifecycle
    def show_centered(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.center().x() - self.W // 2, geo.center().y() - self.H // 2)
        self.show()
        self.raise_()

    def start(self) -> None:
        """Run the animations and the auto-close timer (call once the event loop runs)."""
        import time
        self._t0 = time.monotonic()
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(350)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade.start()
        self._anims.append(fade)
        self.avatar.start()
        if self.voice is not None:
            QTimer.singleShot(250, self.voice.play)
        for i, eff in enumerate(self._effects):
            a = QPropertyAnimation(eff, b"opacity", self)
            a.setDuration(380)
            a.setStartValue(0.0)
            a.setEndValue(1.0)
            a.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anims.append(a)
            QTimer.singleShot(150 + i * 110, a.start)
        QTimer.singleShot(self._ms, self._maybe_close)

    def _maybe_close(self) -> None:
        if self._done:
            return
        # keep open while the mouse is over the card (max 60 s)
        if self.underMouse() and self._waited < 60_000:
            self._waited += 400
            QTimer.singleShot(400, self._maybe_close)
            return
        self.finish()

    def leaveEvent(self, e):  # noqa: N802
        if self._waited:
            QTimer.singleShot(250, self._maybe_close)
        super().leaveEvent(e)

    def keyPressEvent(self, e):  # noqa: N802
        if e.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Space):
            self.finish()
        else:
            super().keyPressEvent(e)

    def _ms_elapsed_early(self) -> bool:
        """True if closed before the voice finished (Esc / close button)."""
        import time
        return (time.monotonic() - getattr(self, "_t0", 0.0)) * 1000 < self._ms - 100

    def finish(self) -> None:
        if self._closing or self._done:
            return
        self._closing = True
        out = QPropertyAnimation(self, b"windowOpacity", self)
        out.setDuration(260)
        out.setStartValue(self.windowOpacity())
        out.setEndValue(0.0)
        out.finished.connect(self._really_close)
        out.start()
        self._anims.append(out)

    def _really_close(self) -> None:
        if self._done:
            return
        self._done = True
        if self.voice is not None and self._ms_elapsed_early():
            self.voice.stop()
        self.close()
        self.finished.emit()
