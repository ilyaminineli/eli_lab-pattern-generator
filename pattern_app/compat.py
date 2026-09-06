from __future__ import annotations

import html
import math
import random
import re

from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QKeySequence, QPainter, QPen, QShortcut, QImage
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QGroupBox, QLabel, QLineEdit, QMenu, QPlainTextEdit, QPushButton, QTabWidget

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
    preferred=["Yu Mincho","YuMincho","MS Mincho","MS PMincho","BIZ UDPMincho","BIZ UDMincho","Noto Serif CJK JP","Noto Serif JP","Source Han Serif","Source Han Serif JP","Hiragino Mincho ProN","Hiragino Mincho Pro","IPAexMincho","IPAMincho","Yu Gothic","YuGothic","Meiryo","Meiryo UI","MS Gothic","MS PGothic","BIZ UDPGothic","BIZ UD Gothic","Noto Sans CJK JP","Noto Sans JP","Source Han Sans","Source Han Sans JP","Hiragino Kaku Gothic ProN","IPAexGothic","IPAGothic","Bahnschrift","Bahnschrift SemiBold","Segoe UI","Segoe UI Variable","Segoe UI Light","Aptos","Aptos Display","Arial","Arial Narrow","Helvetica Neue","Futura","Gill Sans","Garamond","Book Antiqua","Century Gothic","Impact","Trebuchet MS","Consolas","Cascadia Code","Cascadia Mono","JetBrains Mono","IBM Plex Sans","IBM Plex Serif","Inter","Montserrat","Roboto","Roboto Condensed"]
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


def _anchor_rect(anchor, w, h, bw, bh, margin):
    if anchor == "top-left": return margin, margin
    if anchor == "top-center": return (w-bw)/2, margin
    if anchor == "top-right": return w-margin-bw, margin
    if anchor == "center-left": return margin, (h-bh)/2
    if anchor == "center": return (w-bw)/2, (h-bh)/2
    if anchor == "center-right": return w-margin-bw, (h-bh)/2
    if anchor == "bottom-left": return margin, h-margin-bh
    if anchor == "bottom-center": return (w-bw)/2, h-margin-bh
    if anchor == "bottom-right": return w-margin-bw, h-margin-bh
    return None


def _vertical_grid_text_extension(self,result,config):
    settings=self.text_settings; text=settings["text"].replace("\r\n","\n").replace("\r","\n")
    qimage=QImage(config.width,config.height,QImage.Format_ARGB32); qimage.fill(Qt.transparent)
    painter=QPainter(qimage); painter.setRenderHint(QPainter.Antialiasing,True); painter.setRenderHint(QPainter.TextAntialiasing,True)
    font=QFont(settings["font_family"],int(settings["font_size"])); font.setKerning(True)
    try: font.setLetterSpacing(QFont.AbsoluteSpacing,float(settings["tracking"]))
    except Exception: pass
    painter.setFont(font); metrics=painter.fontMetrics(); char_h=metrics.height()*float(settings["line_spacing"])+float(settings.get("tracking",0))
    chars=[c for c in text if c != "\n"]; rng=random.Random(f"{result.seed}:text"); palette=self._palette(rng,config); alpha=max(1,min(255,int(255*settings["opacity"]))); svg=[]
    cols=max(1,int(config.width/max(24,settings["font_size"]*1.35))); rows=max(1,int(config.height/max(24,char_h))); positions=[]; used=0
    for col in range(cols):
        x=config.width-settings["font_size"]*(0.85+col*1.15)
        for row in range(rows):
            if used>=len(chars): break
            char=chars[used]; used+=1; y=settings["font_size"]*0.8+row*char_h; positions.append((char,x,y))
        if used>=len(chars): break
    margin=max(12,float(settings["font_size"])*0.45)
    if positions:
        bw=max(x for _,x,_ in positions)-min(x for _,x,_ in positions)+settings["font_size"]; bh=max(y for _,_,y in positions)-min(y for _,_,y in positions)+char_h
        target=_anchor_rect(settings.get("anchor","free"),config.width,config.height,bw,bh,margin)
        if target:
            dx=target[0]-(min(x for _,x,_ in positions)-settings["font_size"]/2); dy=target[1]-(min(y for _,_,y in positions)-char_h/2); positions=[(c,x+dx,y+dy) for c,x,y in positions]
    def paint(char,x,y):
        color=self._choose_color(rng,palette,config,x,y); painter.save(); painter.translate(x,y); painter.setPen(QPen(QColor(*color,alpha))); painter.drawText(QPointF(0,(metrics.ascent()-metrics.descent())/2),char); painter.restore(); svg.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{html.escape(settings["font_family"])}" font-size="{int(settings["font_size"])}" fill="rgb({color[0]},{color[1]},{color[2]})" fill-opacity="{alpha/255:.3f}" text-anchor="middle" dominant-baseline="middle" xml:space="preserve">{html.escape(char)}</text>')
    for char,x,y in positions: paint(char,x,y)
    painter.end(); raw=bytes(qimage.bits()); text_image=Image.frombytes("RGBA",(qimage.width(),qimage.height()),raw,"raw","BGRA"); result.image=Image.alpha_composite(result.image.convert("RGBA"),text_image)
    if svg: result.svg=result.svg.rsplit("</svg>",1)[0]+"\n"+"\n".join(svg)+"\n</svg>"

_original_text_extension=extensions.EnhancedPatternRenderer._draw_text_extension

def _shift_svg_text(svg,dx,dy):
    def repl(match):
        x=float(match.group(1))+dx; y=float(match.group(2))+dy; attrs=match.group(3)
        attrs=re.sub(r'rotate\((-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\)',lambda m:f'rotate({m.group(1)} {float(m.group(2))+dx:.2f} {float(m.group(3))+dy:.2f})',attrs)
        return f'<text x="{x:.1f}" y="{y:.1f}"{attrs}>'
    return re.sub(r'<text x="(-?[\d.]+)" y="(-?[\d.]+)"([^>]*)>', repl, svg)


def _draw_text_extension(self,result,config):
    mode=self.text_settings.get("mode","flow")
    if mode in {"vertical-grid","tategaki"}: return _vertical_grid_text_extension(self,result,config)
    anchor=self.text_settings.get("anchor","free")
    if anchor == "free / current": anchor="free"
    if anchor == "free": return _original_text_extension(self,result,config)
    base_image=result.image.convert("RGBA"); base_svg=result.svg
    result.image=Image.new("RGBA",(config.width,config.height),(0,0,0,0)); result.svg=base_svg
    _original_text_extension(self,result,config)
    text_layer=result.image; text_svg=result.svg[len(base_svg):]
    bbox=text_layer.getbbox()
    if not bbox:
        result.image=base_image; result.svg=base_svg; return
    l,t,r,b=bbox; bw=r-l; bh=b-t; margin=max(12,int(self.text_settings.get("font_size",72)*0.35)); target=_anchor_rect(anchor,config.width,config.height,bw,bh,margin)
    if target:
        dx=int(round(target[0]-l)); dy=int(round(target[1]-t))
        shifted=Image.new("RGBA",text_layer.size,(0,0,0,0)); shifted.alpha_composite(text_layer,(dx,dy)); text_layer=shifted; text_svg=_shift_svg_text(text_svg,dx,dy)
    result.image=Image.alpha_composite(base_image,text_layer); result.svg=base_svg+text_svg

extensions.EnhancedPatternRenderer._draw_text_extension=_draw_text_extension


EN_TRANSLATIONS={
    "Settings":"設定","File":"ファイル","Generate":"生成","Save PNG":"PNGを保存","Save SVG":"SVGを保存","Save preset":"プリセットを保存","Load preset":"プリセットを読み込む",
    "Composition":"構成","Field":"フィールド","Geometry":"ジオメトリ","Color":"カラー","Layers":"レイヤー","Behavior":"動作","Organic":"有機","Text":"テキスト","Export":"書き出し",
    "Canvas":"キャンバス","Width":"幅","Height":"高さ","Aspect":"比率","Apply aspect":"比率を適用","Seed":"シード","Background":"背景","Palette":"パレット","Symmetry":"対称",
    "Spatial composition":"空間構成","Mode":"モード","Focal X":"焦点X","Focal Y":"焦点Y","Focal strength":"焦点強度","Edge bias":"エッジ偏り","Cluster count":"クラスタ数","Cluster strength":"クラスタ強度","Spacing":"間隔","Position jitter":"位置ジッター",
    "Vector field":"ベクトルフィールド","Strength":"強度","Scale":"スケール","Curvature":"曲率","Steps":"ステップ数","Step size":"ステップ幅","Octaves":"オクターブ",
    "Primitive probability":"プリミティブ確率","Blocks":"ブロック","Circles":"円","Lines":"線","Triangles":"三角形","weight":"重み",
    "Color behavior":"カラー設定","Palette size":"パレット数","Saturation":"彩度","Contrast":"コントラスト","Hue jitter":"色相ジッター","Opacity min":"最小不透明度","Opacity max":"最大不透明度","Color coherence":"色の一貫性",
    "Depth & surface":"奥行き・表面","Layer count":"レイヤー数","Depth":"奥行き","Accent density":"アクセント密度","Gradient background":"グラデーション背景","Raster blur":"ラスターブラー",
    "Controlled behavior":"動作制御","Behavior preset":"動作プリセット","Mutation":"変異","Asymmetry":"非対称","Randomize system":"システムをランダム化",
    "Export current result":"現在の結果を書き出す","Generate / Refresh":"生成 / 更新","Save preset JSON":"プリセットJSONを保存","Load preset JSON":"プリセットJSONを読み込む",
    "Organic forms":"有機形状","Enable organic forms":"有機形状を有効化","Style":"スタイル","Weight":"重み","Lobes":"ローブ数","Wobble":"揺らぎ","Taper":"テーパー","Linework":"線描","Vein count":"葉脈数","Vein wobble":"葉脈の揺らぎ","Long strands":"長いストランド数","Strand length":"ストランド長","Strand wander":"ストランドの蛇行","Strand width":"ストランド幅",
    "Perspective & depth":"遠近感・奥行き","Enable dimensional depth":"立体的奥行きを有効化","Vanishing X":"消失点X","Vanishing Y":"消失点Y","Edge light":"エッジライト",
    "Text / Unicode overlay":"テキスト / Unicode オーバーレイ","Enable text":"テキストを有効化","Arrangement":"配置","Font":"フォント","Size":"サイズ","Tracking":"トラッキング","Line spacing":"行間","Radius":"半径","Wave amount":"波の量","Rotation":"回転",
    "System settings":"システム設定","Language":"言語","English":"English","Japanese":"日本語","Reset window size":"ウィンドウサイズを初期化",
    "Snap position":"スナップ位置","Free / current":"自由 / 現在位置","Top left":"左上","Top center":"上中央","Top right":"右上","Center left":"中央左","Center":"中央","Center right":"中央右","Bottom left":"左下","Bottom center":"下中央","Bottom right":"右下",
    "Procedural composition laboratory":"プロシージャル構成ラボ","Generate a pattern":"パターンを生成"
}
JA_TO_EN={v:k for k,v in EN_TRANSLATIONS.items()}
ANCHORS=[("free / current","自由 / 現在位置"),("top-left","左上"),("top-center","上中央"),("top-right","右上"),("center-left","中央左"),("center","中央"),("center-right","中央右"),("bottom-left","左下"),("bottom-center","下中央"),("bottom-right","右下")]


class MainWindow(extensions.MainWindow):
    """Compatibility wrapper: stable seed previews, Japanese typography, tategaki, snapping, localization and reliable shortcuts."""
    def __init__(self):
        super().__init__(); self._populate_text_fonts(); self._add_vertical_text_mode(); self._add_text_anchor_control(); self._install_settings_menu(); self._apply_language(self.settings.value("language","en"))

    def _populate_text_fonts(self):
        combo=getattr(self,"text_font",None)
        if combo is None:return
        current=combo.currentText(); families=_font_families() or [current or "Sans Serif"]; combo.blockSignals(True); combo.clear(); combo.addItems(families); combo.setCurrentText(current if current in families else ("Bahnschrift" if "Bahnschrift" in families else families[0])); combo.setEditable(True); combo.setInsertPolicy(QComboBox.NoInsert); combo.setMaxVisibleItems(20); combo.blockSignals(False)

    def _add_vertical_text_mode(self):
        combo=getattr(self,"text_mode",None)
        if combo is not None and combo.findText("tategaki")<0: combo.addItem("tategaki")

    def _add_text_anchor_control(self):
        page=None
        for box in self.findChildren(QGroupBox):
            if box.title()=="Text / Unicode overlay": page=box; break
        if page is None or not isinstance(page.layout(),QFormLayout): return
        self.text_anchor=QComboBox()
        for key,label in ANCHORS: self.text_anchor.addItem(label if False else key,key)
        self.text_anchor.setCurrentIndex(0); self.text_anchor.currentIndexChanged.connect(self._request)
        page.layout().addRow("Snap position",self.text_anchor)

    def _config(self):
        if hasattr(self,"result") and self.result is not None and not self.seed.text().strip():
            self.seed.blockSignals(True)
            try:self.seed.setText(self.result.seed)
            finally:self.seed.blockSignals(False)
        cfg=super()._config()
        if hasattr(self,"text_anchor"): self.renderer.text_settings["anchor"]=self.text_anchor.currentData() or "free / current"
        return cfg

    def _finished(self,result,render_id):
        super()._finished(result,render_id)
        if render_id==self.render_id and result.seed and not self.seed.text().strip():
            self.seed.blockSignals(True)
            try:self.seed.setText(result.seed)
            finally:self.seed.blockSignals(False)
        image=result.image
        if image.width>0 and image.height>0:
            up=image.resize((image.width*2,image.height*2),Image.Resampling.BICUBIC); result.image=up.resize((image.width,image.height),Image.Resampling.LANCZOS); self.preview.set_image(pil_to_qimage(result.image))

    def _install_shortcuts(self):
        self._shortcut_objects=[]
        for key,slot in (("Ctrl+G",self.generate),("Ctrl+Shift+P",self.save_png),("Ctrl+Shift+S",self.save_svg),("F5",self.generate)):
            sc=QShortcut(QKeySequence(key),self); sc.setContext(Qt.ApplicationShortcut); sc.activated.connect(slot); self._shortcut_objects.append(sc)

    def _install_settings_menu(self):
        file_action=next((a for a in self.menuBar().actions() if a.text()=="File"),None)
        settings_menu=self.menuBar().addMenu("Settings")
        if file_action is not None: self.menuBar().insertMenu(file_action,settings_menu)
        lang_menu=settings_menu.addMenu("Language")
        self._lang_en=lang_menu.addAction("English"); self._lang_ja=lang_menu.addAction("日本語")
        self._lang_en.setCheckable(True); self._lang_ja.setCheckable(True)
        self._lang_en.triggered.connect(lambda: self._set_language("en")); self._lang_ja.triggered.connect(lambda: self._set_language("ja"))
        settings_menu.addSeparator(); reset=settings_menu.addAction("Reset window size"); reset.triggered.connect(self._reset_window_size)

    def _reset_window_size(self):
        self.resize(1540,940); self.settings.remove("geometry")

    def _set_language(self, language):
        self.settings.setValue("language",language); self._apply_language(language)

    def _translate_text(self, text, language):
        return EN_TRANSLATIONS.get(text,text) if language=="ja" else JA_TO_EN.get(text,text)

    def _apply_language(self, language):
        language="ja" if language=="ja" else "en"
        for widget in self.findChildren(QGroupBox): widget.setTitle(self._translate_text(widget.title(),language))
        for widget in self.findChildren((QLabel,QPushButton,QCheckBox,QLineEdit,QPlainTextEdit)):
            if isinstance(widget,QPlainTextEdit): continue
            try: widget.setText(self._translate_text(widget.text(),language))
            except Exception: pass
        tabs=self.findChild(QTabWidget)
        if tabs is not None:
            for i in range(tabs.count()): tabs.setTabText(i,self._translate_text(tabs.tabText(i),language))
        if hasattr(self,"text_anchor"):
            current=self.text_anchor.currentData() or "free / current"; self.text_anchor.blockSignals(True); self.text_anchor.clear()
            for key,ja in ANCHORS: self.text_anchor.addItem(key if language=="en" else ja,key)
            self.text_anchor.setCurrentIndex(max(0,self.text_anchor.findData(current))); self.text_anchor.blockSignals(False)
            for layout in self.findChildren(QFormLayout):
                for row in range(layout.rowCount()):
                    label=layout.itemAt(row,QFormLayout.LabelRole)
                    if label is not None and label.widget() is not None:
                        w=label.widget()
                        if w.text()=="Snap position" or w.text()=="スナップ位置": w.setText(self._translate_text("Snap position",language))
        for action in self.menuBar().actions(): action.setText(self._translate_text(action.text(),language))
        self._settings_menu.setTitle(self._translate_text("Settings",language)) if hasattr(self,"_settings_menu") else None
        self._lang_en.setChecked(language=="en"); self._lang_ja.setChecked(language=="ja"); self._localized_language=language

EnhancedPatternRenderer=extensions.EnhancedPatternRenderer
__all__=["MainWindow","EnhancedPatternRenderer"]
