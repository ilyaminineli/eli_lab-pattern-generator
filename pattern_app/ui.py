from __future__ import annotations
import json
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QSettings, QSize, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtGui import QAction, QColor, QImage, QPixmap, QKeySequence
from PySide6.QtWidgets import QApplication, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QPushButton
from .generator import PatternConfig, PatternRenderer
from .palettes import ALL_PALETTES, BUILTIN_PALETTES, DATA

def build_app(): return QApplication.instance() or QApplication([])
def pil_to_qimage(image):
    rgba=image.convert('RGBA'); return QImage(rgba.tobytes('raw','RGBA'),rgba.width,rgba.height,rgba.width*4,QImage.Format_RGBA8888).copy()
class WorkerSignals(QObject): finished=Signal(object,int); failed=Signal(str,int)
class RenderTask(QRunnable):
    def __init__(self,renderer,config,rid): super().__init__(); self.renderer=renderer; self.config=config; self.rid=rid; self.signals=WorkerSignals()
    @Slot()
    def run(self):
        try:self.signals.finished.emit(self.renderer.generate(self.config),self.rid)
        except Exception as e:self.signals.failed.emit(str(e),self.rid)
class PreviewWidget(QLabel):
    def __init__(self): super().__init__(); self._image=None; self.setAlignment(Qt.AlignCenter); self.setMinimumSize(520,420); self.setFrameShape(QFrame.StyledPanel); self.setText('Generate a pattern')
    def set_image(self,img): self._image=img; self._fit()
    def resizeEvent(self,e): super().resizeEvent(e); self._fit()
    def _fit(self):
        if self._image:self.setPixmap(QPixmap.fromImage(self._image).scaled(self.size()-QSize(20,20),Qt.KeepAspectRatio,Qt.SmoothTransformation))
class MainWindow(QMainWindow):
    RATIOS={'square':(1,1),'landscape':(16,9),'portrait':(9,16),'ultrawide':(21,9)}
    def __init__(self):
        super().__init__(); self.setWindowTitle('eli_lab Pattern Generator'); self.resize(1540,940); self.renderer=PatternRenderer(); self.pool=QThreadPool.globalInstance(); self.result=None; self.rid=0; self.settings=QSettings('eli_lab','PatternGenerator'); self.loading=False; self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(160); self.timer.timeout.connect(self.generate); self._build(); self._restore(); self.generate()
    def _group(self,title): box=QGroupBox(title); return box,QFormLayout(box)
    def _double(self,a,b,v,d=2,st=None): w=QDoubleSpinBox(); w.setRange(a,b); w.setDecimals(d); w.setSingleStep(st or max((b-a)/100,.0001)); w.setValue(v); return w
    def _combo(self,items): w=QComboBox(); w.addItems(items); return w
    def _build(self):
        c=QWidget(); self.setCentralWidget(c); root=QHBoxLayout(c); controls=QFrame(); left=QVBoxLayout(controls); left.addWidget(QLabel('eli_lab / PATTERN GENERATOR')); left.addWidget(QLabel('Procedural composition laboratory')); tabs=QTabWidget(); sc=QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(tabs); left.addWidget(sc,1); root.addWidget(controls,0)
        tabs.addTab(self._canvas(),'Canvas'); tabs.addTab(self._field(),'Field'); tabs.addTab(self._geometry(),'Geometry'); tabs.addTab(self._organic(),'Organic'); tabs.addTab(self._color(),'Color'); tabs.addTab(self._layers(),'Layers'); tabs.addTab(self._behavior(),'Behavior'); tabs.addTab(self._export(),'Export')
        right=QVBoxLayout(); self.preview=PreviewWidget(); right.addWidget(self.preview,1); row=QHBoxLayout(); self.status=QLabel('Ready'); self.seed_label=QLabel(''); row.addWidget(self.status); row.addStretch(); row.addWidget(self.seed_label); right.addLayout(row); root.addLayout(right,1)
    def _canvas(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Canvas'); self.width=QSpinBox(); self.width.setRange(64,8192); self.width.setValue(1600); self.height=QSpinBox(); self.height.setRange(64,8192); self.height.setValue(900); self.aspect=self._combo(['custom',*self.RATIOS]); ap=QPushButton('Apply aspect'); ap.clicked.connect(self.apply_aspect); self.seed=QLineEdit(); self.seed.setPlaceholderText('Fixed seed = reproducible artwork'); self.background=QLineEdit('#111111'); pk=QPushButton('Pick'); pk.clicked.connect(self.pick_background); bg=QHBoxLayout(); bg.addWidget(self.background); bg.addWidget(pk); self.palette_mode=QComboBox(); self.palette_mode.addItem('random','random'); self.palette_mode.addItem('pastel','pastel'); self.palette_mode.addItem('LGBTQ+ / all unique colors','lgbtq-all'); self.palette_mode.insertSeparator(self.palette_mode.count());
        for k,pal in ALL_PALETTES.items():
            if k in BUILTIN_PALETTES:self.palette_mode.addItem(pal.name,k)
        self.palette_mode.insertSeparator(self.palette_mode.count());
        for k,n,_ in DATA:self.palette_mode.addItem(n,k)
        self.symmetry=self._combo(['none','mirror','radial','grid']);
        for n,w in [('Width',self.width),('Height',self.height),('Aspect',self.aspect),('',ap),('Seed',self.seed),('Background',bg),('Palette',self.palette_mode),('Symmetry',self.symmetry)]:f.addRow(n,w)
        l.addWidget(b); b,f=self._group('Composition'); self.composition_mode=self._combo(['balanced','focal','clustered','edge','diagonal']); self.focal_x=self._double(0,1,.5); self.focal_y=self._double(0,1,.5); self.focal_strength=self._double(0,1,.6); self.edge_bias=self._double(-1,1,0); self.cluster_count=QSpinBox(); self.cluster_count.setRange(1,24); self.cluster_count.setValue(4); self.cluster_strength=self._double(0,1,.25); self.spacing=self._double(0,1,.15); self.jitter=self._double(0,1,.08)
        for n,w in [('Mode',self.composition_mode),('Focal X',self.focal_x),('Focal Y',self.focal_y),('Focal strength',self.focal_strength),('Edge bias',self.edge_bias),('Cluster count',self.cluster_count),('Cluster strength',self.cluster_strength),('Spacing',self.spacing),('Jitter',self.jitter)]:f.addRow(n,w)
        l.addWidget(b); l.addStretch(); return p
    def _field(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Vector field'); self.field_mode=self._combo(['none','noise','swirl','vortex','waves','radial']); self.field_strength=self._double(0,1.5,.65); self.field_scale=self._double(.0005,.08,.012,4); self.field_curvature=self._double(0,1,.35); self.field_steps=QSpinBox(); self.field_steps.setRange(4,96); self.field_steps.setValue(24); self.field_step_size=self._double(1,80,18,1); self.noise_octaves=QSpinBox(); self.noise_octaves.setRange(1,8); self.noise_octaves.setValue(3)
        for n,w in [('Field',self.field_mode),('Strength',self.field_strength),('Scale',self.field_scale),('Curvature',self.field_curvature),('Steps',self.field_steps),('Step size',self.field_step_size),('Octaves',self.noise_octaves)]:f.addRow(n,w)
        l.addWidget(b); l.addStretch(); return p
    def _geometry(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Geometry'); self.grid_size=QSpinBox(); self.grid_size.setRange(4,48); self.grid_size.setValue(14); self.shape_scale=self._double(.05,1.5,.72); self.scale_variance=self._double(0,1,.35); self.rotation=self._double(0,360,0,0,1); self.rotation_jitter=self._double(0,3.14159,.7); self.corner_roundness=self._double(0,1,.35); self.line_complexity=self._double(.05,1,.55); self.overlap=self._double(0,1,.2)
        for n,w in [('Grid',self.grid_size),('Shape scale',self.shape_scale),('Scale variance',self.scale_variance),('Rotation',self.rotation),('Rotation jitter',self.rotation_jitter),('Corner roundness',self.corner_roundness),('Line complexity',self.line_complexity),('Overlap',self.overlap)]:f.addRow(n,w)
        l.addWidget(b); b,f=self._group('Primitive probability'); self.use_blocks=QCheckBox('Blocks'); self.use_blocks.setChecked(True); self.block_weight=self._double(0,3,1); self.use_circles=QCheckBox('Circles'); self.use_circles.setChecked(True); self.circle_weight=self._double(0,3,1); self.use_lines=QCheckBox('Lines'); self.use_lines.setChecked(True); self.line_weight=self._double(0,3,1); self.use_triangles=QCheckBox('Triangles'); self.use_triangles.setChecked(True); self.triangle_weight=self._double(0,3,1)
        for cb,w in ((self.use_blocks,self.block_weight),(self.use_circles,self.circle_weight),(self.use_lines,self.line_weight),(self.use_triangles,self.triangle_weight)):r=QHBoxLayout();r.addWidget(cb);r.addWidget(QLabel('weight'));r.addWidget(w);f.addRow(r)
        l.addWidget(b); l.addStretch(); return p
    def _organic(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Organic forms'); self.use_organic=QCheckBox('Enable organic forms'); self.use_organic.setChecked(True); self.organic_style=self._combo(['amoeba','blob','petal','cell','droplet','leaf']); self.organic_weight=self._double(0,4,1); self.organic_lobes=QSpinBox(); self.organic_lobes.setRange(3,18); self.organic_lobes.setValue(7); self.organic_wobble=self._double(0,1,.55); self.organic_taper=self._double(0,1,.25); self.organic_veins=QCheckBox('Internal veins / tendrils'); self.organic_veins.setChecked(True)
        for n,w in [('Enable',self.use_organic),('Style',self.organic_style),('Weight',self.organic_weight),('Lobes',self.organic_lobes),('Wobble',self.organic_wobble),('Taper',self.organic_taper),('',self.organic_veins)]:f.addRow(n,w)
        l.addWidget(b); l.addWidget(QLabel('Organic silhouettes are deterministic radial deformations: amoebas, blobs, petals, cells, droplets and leaves.')); l.addStretch(); return p
    def _color(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Color behavior'); self.palette_size=QSpinBox(); self.palette_size.setRange(2,16); self.palette_size.setValue(6); self.saturation=self._double(0,1.5,1); self.contrast=self._double(0,1,.5); self.hue_jitter=self._double(0,1,.08); self.opacity_min=self._double(.05,1,.3); self.opacity_max=self._double(.05,1,.85); self.color_coherence=self._double(0,1,.6); self.lgbtq_lock=QCheckBox('Preserve Pride flag colors'); self.lgbtq_lock.setChecked(True)
        for n,w in [('Palette size',self.palette_size),('Saturation',self.saturation),('Contrast',self.contrast),('Hue jitter',self.hue_jitter),('Opacity min',self.opacity_min),('Opacity max',self.opacity_max),('Color coherence',self.color_coherence),('',self.lgbtq_lock)]:f.addRow(n,w)
        l.addWidget(b); l.addWidget(QLabel('The palette registry contains the 43-flag curated baseline plus an aggregate all-colors mode.')); l.addStretch(); return p
    def _layers(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Depth & surface'); self.layer_count=QSpinBox(); self.layer_count.setRange(1,8); self.layer_count.setValue(1); self.depth=self._double(0,1,.45); self.accent_density=self._double(0,1,.25); self.gradient=QCheckBox('Gradient background'); self.blur=self._double(0,12,0,1)
        for n,w in [('Layer count',self.layer_count),('Depth',self.depth),('Accent density',self.accent_density),('',self.gradient),('Raster blur',self.blur)]:f.addRow(n,w)
        l.addWidget(b); l.addStretch(); return p
    def _behavior(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Controlled behavior'); self.behavior=self._combo(['calm','organic','architectural','chaotic','ritual']); self.mutation=self._double(0,1,.25); self.asymmetry=self._double(0,1,.35); f.addRow('Behavior preset',self.behavior); f.addRow('Mutation',self.mutation); f.addRow('Asymmetry',self.asymmetry); l.addWidget(b); r=QHBoxLayout(); q=QPushButton('Randomize system'); q.clicked.connect(self.randomize); g=QPushButton('Generate'); g.clicked.connect(self.generate); r.addWidget(q); r.addWidget(g); l.addLayout(r); l.addStretch(); return p
    def _export(self):
        p=QWidget(); l=QVBoxLayout(p); b,f=self._group('Export'); self.generate_button=QPushButton('Generate / Refresh'); self.generate_button.clicked.connect(self.generate); a=QPushButton('Save PNG'); a.clicked.connect(self.save_png); z=QPushButton('Save SVG'); z.clicked.connect(self.save_svg); sp=QPushButton('Save preset JSON'); sp.clicked.connect(self.save_preset); lp=QPushButton('Load preset JSON'); lp.clicked.connect(self.load_preset)
        for w in (self.generate_button,a,z,sp,lp):w.setMinimumHeight(34);f.addRow(w)
        l.addWidget(b); l.addStretch(); return p
    def _menu(self):
        m=self.menuBar().addMenu('File')
        for text,slot,sc in [('Generate',self.generate,'Ctrl+G'),('Save PNG',self.save_png,'Ctrl+Shift+P'),('Save SVG',self.save_svg,'Ctrl+Shift+S'),('Save preset',self.save_preset,None),('Load preset',self.load_preset,None)]:a=QAction(text,self);a.triggered.connect(slot);m.addAction(a);a.setShortcut(QKeySequence(sc)) if sc else None
    def _restore(self):
        g=self.settings.value('geometry'); self.restoreGeometry(g) if g else None; self._menu(); self._wire()
    def _wire(self):
        widgets=[]
        for v in vars(self).values():
            if isinstance(v,(QLineEdit,QComboBox,QCheckBox,QSpinBox,QDoubleSpinBox)):widgets.append(v)
        for w in widgets:
            if isinstance(w,QLineEdit):w.textChanged.connect(self._request)
            elif isinstance(w,QComboBox):w.currentIndexChanged.connect(self._request)
            elif isinstance(w,QCheckBox):w.toggled.connect(self._request)
            else:w.valueChanged.connect(self._request)
    def _request(self,*_):
        if not self.loading:self.timer.start()
    def _config(self):
        return PatternConfig(width=self.width.value(),height=self.height.value(),seed=self.seed.text(),background=self.background.text(),composition_mode=self.composition_mode.currentText(),symmetry=self.symmetry.currentText(),focal_x=self.focal_x.value(),focal_y=self.focal_y.value(),focal_strength=self.focal_strength.value(),edge_bias=self.edge_bias.value(),cluster_count=self.cluster_count.value(),cluster_strength=self.cluster_strength.value(),spacing=self.spacing.value(),jitter=self.jitter.value(),field_mode=self.field_mode.currentText(),field_strength=self.field_strength.value(),field_scale=self.field_scale.value(),field_curvature=self.field_curvature.value(),field_steps=self.field_steps.value(),field_step_size=self.field_step_size.value(),noise_octaves=self.noise_octaves.value(),grid_size=self.grid_size.value(),shape_scale=self.shape_scale.value(),scale_variance=self.scale_variance.value(),rotation=self.rotation.value(),rotation_jitter=self.rotation_jitter.value(),corner_roundness=self.corner_roundness.value(),line_complexity=self.line_complexity.value(),overlap=self.overlap.value(),use_blocks=self.use_blocks.isChecked(),use_circles=self.use_circles.isChecked(),use_lines=self.use_lines.isChecked(),use_triangles=self.use_triangles.isChecked(),use_organic=self.use_organic.isChecked(),organic_style=self.organic_style.currentText(),organic_weight=self.organic_weight.value(),organic_lobes=self.organic_lobes.value(),organic_wobble=self.organic_wobble.value(),organic_taper=self.organic_taper.value(),organic_veins=self.organic_veins.isChecked(),block_weight=self.block_weight.value(),circle_weight=self.circle_weight.value(),line_weight=self.line_weight.value(),triangle_weight=self.triangle_weight.value(),palette_mode=self.palette_mode.currentData(),palette_size=self.palette_size.value(),saturation=self.saturation.value(),contrast=self.contrast.value(),hue_jitter=0 if self.lgbtq_lock.isChecked() and self.palette_mode.currentData() not in {'random','pastel'} else self.hue_jitter.value(),opacity_min=self.opacity_min.value(),opacity_max=self.opacity_max.value(),color_coherence=self.color_coherence.value(),layer_count=self.layer_count.value(),depth=self.depth.value(),accent_density=self.accent_density.value(),gradient=self.gradient.isChecked(),blur=self.blur.value(),behavior=self.behavior.currentText(),mutation=self.mutation.value(),asymmetry=self.asymmetry.value()).normalized()
    def generate(self):
        if not hasattr(self,'palette_mode'):return
        self.rid+=1; rid=self.rid; self.status.setText('Rendering…'); self.generate_button.setEnabled(False); t=RenderTask(self.renderer,self._config(),rid); t.signals.finished.connect(self._finished); t.signals.failed.connect(self._failed); self.pool.start(t)
    def _finished(self,r,rid):
        if rid!=self.rid:return
        self.result=r; self.preview.set_image(pil_to_qimage(r.image)); self.seed_label.setText(f'Seed: {r.seed} · {r.elapsed:.2f}s'); self.status.setText('Ready'); self.generate_button.setEnabled(True)
    def _failed(self,msg,rid):
        if rid!=self.rid:return
        self.status.setText('Error'); self.generate_button.setEnabled(True); QMessageBox.critical(self,'Render error',msg)
    def apply_aspect(self):
        if self.aspect.currentText() in self.RATIOS:a,b=self.RATIOS[self.aspect.currentText()]; self.height.setValue(max(64,round(self.width.value()*b/a)))
    def pick_background(self):
        c=QColorDialog.getColor(QColor(self.background.text()),self); self.background.setText(c.name()) if c.isValid() else None
    def randomize(self):
        import random
        self.seed.setText(str(random.randint(0,2**31-1))); self.palette_mode.setCurrentIndex(random.randrange(self.palette_mode.count())); self.organic_style.setCurrentIndex(random.randrange(self.organic_style.count()))
    def save_png(self):
        if not self.result:return
        p,_=QFileDialog.getSaveFileName(self,'Save PNG','','PNG files (*.png)'); self.result.image.save(p) if p else None
    def save_svg(self):
        if not self.result:return
        p,_=QFileDialog.getSaveFileName(self,'Save SVG','','SVG files (*.svg)'); Path(p).write_text(self.result.svg,encoding='utf-8') if p else None
    def save_preset(self):
        p,_=QFileDialog.getSaveFileName(self,'Save preset','','JSON files (*.json)'); Path(p).write_text(json.dumps(self._config().to_dict(),indent=2),encoding='utf-8') if p else None
    def load_preset(self):
        p,_=QFileDialog.getOpenFileName(self,'Load preset','','JSON files (*.json)')
        if not p:return
        try:data=json.loads(Path(p).read_text(encoding='utf-8')); self.loading=True; fields={'width':self.width,'height':self.height,'seed':self.seed,'background':self.background,'composition_mode':self.composition_mode,'symmetry':self.symmetry,'focal_x':self.focal_x,'focal_y':self.focal_y,'focal_strength':self.focal_strength,'edge_bias':self.edge_bias,'cluster_count':self.cluster_count,'cluster_strength':self.cluster_strength,'spacing':self.spacing,'jitter':self.jitter,'field_mode':self.field_mode,'field_strength':self.field_strength,'field_scale':self.field_scale,'field_curvature':self.field_curvature,'field_steps':self.field_steps,'field_step_size':self.field_step_size,'noise_octaves':self.noise_octaves,'grid_size':self.grid_size,'shape_scale':self.shape_scale,'scale_variance':self.scale_variance,'rotation':self.rotation,'rotation_jitter':self.rotation_jitter,'corner_roundness':self.corner_roundness,'line_complexity':self.line_complexity,'overlap':self.overlap,'use_blocks':self.use_blocks,'use_circles':self.use_circles,'use_lines':self.use_lines,'use_triangles':self.use_triangles,'use_organic':self.use_organic,'organic_style':self.organic_style,'organic_weight':self.organic_weight,'organic_lobes':self.organic_lobes,'organic_wobble':self.organic_wobble,'organic_taper':self.organic_taper,'organic_veins':self.organic_veins,'block_weight':self.block_weight,'circle_weight':self.circle_weight,'line_weight':self.line_weight,'triangle_weight':self.triangle_weight,'palette_size':self.palette_size,'saturation':self.saturation,'contrast':self.contrast,'hue_jitter':self.hue_jitter,'opacity_min':self.opacity_min,'opacity_max':self.opacity_max,'color_coherence':self.color_coherence,'layer_count':self.layer_count,'depth':self.depth,'accent_density':self.accent_density,'gradient':self.gradient,'blur':self.blur,'behavior':self.behavior,'mutation':self.mutation,'asymmetry':self.asymmetry}
        except Exception as e:QMessageBox.critical(self,'Preset error',str(e));return
        try:
            for k,w in fields.items():
                if k not in data:continue
                v=data[k]
                if isinstance(w,QLineEdit):w.setText(str(v))
                elif isinstance(w,QComboBox):i=w.findText(str(v));w.setCurrentIndex(i if i>=0 else 0)
                elif isinstance(w,QCheckBox):w.setChecked(bool(v))
                else:w.setValue(v)
            if 'palette_mode' in data:i=self.palette_mode.findData(data['palette_mode']);self.palette_mode.setCurrentIndex(i if i>=0 else 0)
        finally:self.loading=False
        self.generate()
    def closeEvent(self,e): self.settings.setValue('geometry',self.saveGeometry());e.accept()
