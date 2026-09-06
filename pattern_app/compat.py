from __future__ import annotations

import html
import math
import random

from PIL import Image, ImageFilter
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont, QFontDatabase, QKeySequence, QPainter, QPen, QColor, QShortcut, QImage
from PySide6.QtWidgets import QComboBox

from . import extensions
from .generator import PatternRenderer as BaseRenderer, _rotate
from .ui import pil_to_qimage


def _compatible_shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha):
    settings = getattr(self, "perspective_settings", {})
    if not settings.get("enabled", False) or settings.get("strength", 0) <= 0:
        return BaseRenderer._shape(self, draw, svg, cfg, rng, shape, cx, cy, size, rotation, color, alpha)
    vx = cfg.width * float(settings.get("vanishing_x", 0.5)); vy = cfg.height * float(settings.get("vanishing_y", 0.42))
    dx = cx - vx; dy = cy - vy; distance = max(1.0, math.hypot(dx, dy))
    strength = float(settings.get("strength", 0.18)); depth = size * strength * (0.65 + 0.35 * min(1.0, distance / max(cfg.width, cfg.height)))
    ox = dx / distance * depth; oy = dy / distance * depth
    shadow = tuple(max(0, int(c * 0.42)) for c in color); shadow_alpha = max(24, int(alpha * 0.42))
    if shape in {"block", "tri"}:
        half = size * 0.5
        if shape == "tri": front = _rotate([(cx, cy-half), (cx-half, cy+half), (cx+half, cy+half)], rotation, cx, cy)
        else: front = _rotate([(cx-half,cy-half),(cx+half,cy-half),(cx+half,cy+half),(cx-half,cy+half)], rotation, cx, cy)
        back = [(x+ox,y+oy) for x,y in front]; face_alpha = max(18, int(alpha*0.30))
        for i in range(len(front)):
            a,b=front[i],front[(i+1)%len(front)]; bi,bj=back[i],back[(i+1)%len(back)]
            draw.polygon([a,b,bj,bi], fill=(*shadow,face_alpha))
            svg.append(f'<polygon points="{a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f} {bj[0]:.1f},{bj[1]:.1f} {bi[0]:.1f},{bi[1]:.1f}" fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{face_alpha/255:.3f}"/>')
        draw.polygon(back,fill=(*shadow,shadow_alpha)); svg.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in back)}" fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{shadow_alpha/255:.3f}"/>')
    elif shape == "circle":
        r=size*.5; draw.ellipse((cx-r+ox,cy-r+oy,cx+r+ox,cy+r+oy),fill=(*shadow,shadow_alpha)); svg.append(f'<ellipse cx="{cx+ox:.1f}" cy="{cy+oy:.1f}" rx="{r:.1f}" ry="{r:.1f}" fill="rgb({shadow[0]},{shadow[1]},{shadow[2]})" fill-opacity="{shadow_alpha/255:.3f}"/>')
    elif shape == "line":
        half=size*.5; count=3+int(cfg.line_complexity*6); front=[]
        for i in range(count):
            t=i/max(1,count-1); front.append((cx-half+t*size,cy+math.sin(t*math.pi*2+rotation)*size*.25))
        front=_rotate(front,rotation,cx,cy); back=[(x+ox,y+oy) for x,y in front]; width=max(1,int((1+cfg.depth*5)*size/120)); draw.line(back,fill=(*shadow,shadow_alpha),width=width,joint="curve"); svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in back)}" fill="none" stroke="rgb({shadow[0]},{shadow[1]},{shadow[2]})" stroke-opacity="{shadow_alpha/255:.3f}" stroke-width="{width}" stroke-linecap="round"/>')
    BaseRenderer._shape(self,draw,svg,cfg,rng,shape,cx,cy,size,rotation,color,alpha)
    edge_light=float(settings.get("edge_light",.28))
    if edge_light>0 and shape in {"block","tri","circle"}:
        hi=tuple(min(255,int(c+(255-c)*edge_light)) for c in color); ha=max(12,int(alpha*.20)); r=size*.5; draw.ellipse((cx-r*.48,cy-r*.76,cx-r*.20,cy-r*.48),fill=(*hi,ha)); svg.append(f'<ellipse cx="{cx-r*.34:.1f}" cy="{cy-r*.62:.1f}" rx="{r*.14:.1f}" ry="{r*.14:.1f}" fill="rgb({hi[0]},{hi[1]},{hi[2]})" fill-opacity="{ha/255:.3f}"/>')


extensions.EnhancedPatternRenderer._shape = _compatible_shape


def _font_families() -> list[str]:
    try:
        db=QFontDatabase(); all_families=set(db.families())
        try: japanese=set(db.families(QFontDatabase.WritingSystem.Japanese))
        except Exception: japanese=set()
    except Exception: all_families=set(); japanese=set()
    preferred=[
        "Yu Mincho","YuMincho","MS Mincho","MS PMincho","BIZ UDPMincho","BIZ UDMincho","Noto Serif CJK JP","Noto Serif JP","Source Han Serif","Source Han Serif JP","Hiragino Mincho ProN","Hiragino Mincho Pro","IPAexMincho","IPAMincho","Yu Gothic","YuGothic","Meiryo","Meiryo UI","MS Gothic","MS PGothic","BIZ UDPGothic","BIZ UD Gothic","Noto Sans CJK JP","Noto Sans JP","Source Han Sans","Source Han Sans JP","Hiragino Kaku Gothic ProN","IPAexGothic","IPAGothic","Bahnschrift","Bahnschrift SemiBold","Segoe UI","Segoe UI Variable","Segoe UI Light","Aptos","Aptos Display","Arial","Arial Narrow","Helvetica Neue","Futura","Gill Sans","Garamond","Book Antiqua","Century Gothic","Impact","Trebuchet MS","Consolas","Cascadia Code","Cascadia Mono","JetBrains Mono","IBM Plex Sans","IBM Plex Serif","Inter","Montserrat","Roboto","Roboto Condensed"
    ]
    ordered=[]; seen=set()
    for family in preferred:
        if family in all_families and family not in seen: ordered.append(family); seen.add(family)
    for family in sorted(japanese,key=str.casefold):
        if family not in seen: ordered.append(family); seen.add(family)
    keywords=("display","condensed","mono","serif","gothic","mincho","script","slab","hand","sans","headline","black","light","variable","retro","pixel")
    for family in sorted(all_families,key=str.casefold):
        low=family.casefold()
        if family not in seen and any(k in low for k in keywords): ordered.append(family); seen.add(family)
    return ordered


def _vertical_grid_text_extension(self,result,config):
    settings=self.text_settings; text=settings["text"].replace("\r\n","\n").replace("\r","\n")
    qimage=QImage(config.width,config.height,QImage.Format_ARGB32); qimage.fill(Qt.transparent)
    painter=QPainter(qimage); painter.setRenderHint(QPainter.Antialiasing,True); painter.setRenderHint(QPainter.TextAntialiasing,True)
    font=QFont(settings["font_family"],int(settings["font_size"])); font.setKerning(True)
    try: font.setLetterSpacing(QFont.AbsoluteSpacing,float(settings["tracking"]))
    except Exception: pass
    painter.setFont(font); metrics=painter.fontMetrics(); char_h=metrics.height()*float(settings["line_spacing"])
    chars=[c for c in text if c != "\n"]; rng=random.Random(f"{result.seed}:text"); palette=self._palette(rng,config); alpha=max(1,min(255,int(255*settings["opacity"]))); svg=[]
    def paint(char,x,y):
        color=self._choose_color(rng,palette,config,x,y); painter.save(); painter.translate(x,y); painter.setPen(QPen(QColor(*color,alpha))); painter.drawText(QPointF(0,(metrics.ascent()-metrics.descent())/2),char); painter.restore(); svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{html.escape(settings["font_family"])}" font-size="{int(settings["font_size"])}" fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{alpha/255:.3f}" text-anchor="middle" dominant-baseline="middle">{html.escape(char)}</text>')
    cols=max(1,int(config.width/max(24,settings["font_size"]*1.35))); rows=max(1,int(config.height/max(24,char_h))); used=0
    for col in range(cols):
        x=config.width-settings["font_size"]*(0.85+col*1.15)
        for row in range(rows):
            if used>=len(chars): break
            char=chars[used]; used+=1; y=settings["font_size"]*0.8+row*char_h; paint(char,x,y)
        if used>=len(chars): break
    painter.end(); raw=bytes(qimage.bits()); text_image=Image.frombytes("RGBA",(qimage.width(),qimage.height()),raw,"raw","BGRA")
    result.image=Image.alpha_composite(result.image.convert("RGBA"),text_image)
    if svg: result.svg=result.svg.rsplit("</svg>",1)[0]+"\n"+"\n".join(svg)+"\n</svg>"


_original_text_extension=extensions.EnhancedPatternRenderer._draw_text_extension

def _draw_text_extension(self,result,config):
    if self.text_settings.get("mode")=="vertical-grid": return _vertical_grid_text_extension(self,result,config)
    return _original_text_extension(self,result,config)

extensions.EnhancedPatternRenderer._draw_text_extension=_draw_text_extension


class MainWindow(extensions.MainWindow):
    """Compatibility wrapper: stable seed previews, Japanese typography and reliable shortcuts."""
    def __init__(self):
        super().__init__(); self._populate_text_fonts(); self._add_vertical_text_mode()

    def _populate_text_fonts(self):
        combo=getattr(self,"text_font",None)
        if combo is None:return
        current=combo.currentText(); families=_font_families() or [current or "Sans Serif"]; combo.blockSignals(True); combo.clear(); combo.addItems(families); combo.setCurrentText(current if current in families else ("Bahnschrift" if "Bahnschrift" in families else families[0])); combo.setEditable(True); combo.setInsertPolicy(QComboBox.NoInsert); combo.setMaxVisibleItems(20); combo.blockSignals(False)

    def _add_vertical_text_mode(self):
        combo=getattr(self,"text_mode",None)
        if combo is not None and combo.findText("vertical-grid")<0: combo.addItem("vertical-grid")

    def _config(self):
        if hasattr(self,"result") and self.result is not None and not self.seed.text().strip():
            self.seed.blockSignals(True)
            try:self.seed.setText(self.result.seed)
            finally:self.seed.blockSignals(False)
        return super()._config()

    def _finished(self,result,render_id):
        super()._finished(result,render_id)
        if render_id==self.render_id and result.seed and not self.seed.text().strip():
            self.seed.blockSignals(True)
            try:self.seed.setText(result.seed)
            finally:self.seed.blockSignals(False)
        image=result.image
        if image.width>0 and image.height>0:
            up=image.resize((image.width*2,image.height*2),Image.Resampling.BICUBIC); result.image=up.resize((image.width,image.height),Image.Resampling.LANCZOS)
            self.preview.set_image(pil_to_qimage(result.image))

    def _install_shortcuts(self):
        self._shortcut_objects=[]
        for key,slot in (("Ctrl+G",self.generate),("Ctrl+Shift+P",self.save_png),("Ctrl+Shift+S",self.save_svg),("F5",self.generate)):
            sc=QShortcut(QKeySequence(key),self); sc.setContext(Qt.ApplicationShortcut); sc.activated.connect(slot); self._shortcut_objects.append(sc)

EnhancedPatternRenderer=extensions.EnhancedPatternRenderer
__all__=["MainWindow","EnhancedPatternRenderer"]
