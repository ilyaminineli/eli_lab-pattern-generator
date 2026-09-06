from __future__ import annotations
import html, math, random, time
from dataclasses import asdict, dataclass, replace
from PIL import Image, ImageDraw, ImageFilter
from .palettes import ALL_PALETTES, ALL_LGBTQ_COLORS
try:
    from opensimplex import OpenSimplex
except ImportError:
    OpenSimplex=None
PALETTES={k:p.colors for k,p in ALL_PALETTES.items()}

@dataclass(slots=True)
class PatternConfig:
    width:int=1600; height:int=900; seed:str=''; background:str='#111111'; density:float=.55; complexity:float=.65
    composition_mode:str='balanced'; symmetry:str='none'; focal_x:float=.5; focal_y:float=.5; focal_strength:float=.6; edge_bias:float=0; cluster_count:int=4; cluster_strength:float=.25; spacing:float=.15; jitter:float=.08
    field_mode:str='noise'; field_strength:float=.65; field_scale:float=.012; field_curvature:float=.35; field_steps:int=24; field_step_size:float=18; noise_octaves:int=3
    grid_size:int=14; shape_scale:float=.72; scale_variance:float=.35; rotation:float=0; rotation_jitter:float=.7; corner_roundness:float=.35; line_complexity:float=.55; overlap:float=.2
    use_blocks:bool=True; use_circles:bool=True; use_lines:bool=True; use_triangles:bool=True; use_organic:bool=True
    organic_style:str='amoeba'; organic_weight:float=1; organic_lobes:int=7; organic_wobble:float=.55; organic_taper:float=.25; organic_veins:bool=True
    block_weight:float=1; circle_weight:float=1; line_weight:float=1; triangle_weight:float=1
    palette_mode:str='random'; palette_size:int=6; saturation:float=1; contrast:float=.5; hue_jitter:float=.08; opacity_min:float=.3; opacity_max:float=.85; color_coherence:float=.6
    layer_count:int=1; depth:float=.45; accent_density:float=.25; gradient:bool=False; blur:float=0
    behavior:str='organic'; mutation:float=.25; asymmetry:float=.35
    def normalized(self):
        return replace(self,width=max(64,min(8192,int(self.width))),height=max(64,min(8192,int(self.height))),seed=str(self.seed).strip(),background=self.background.strip() or '#111111',density=max(.02,min(1,float(self.density))),complexity=max(.05,min(1,float(self.complexity))),composition_mode=self.composition_mode if self.composition_mode in {'balanced','focal','clustered','edge','diagonal'} else 'balanced',symmetry=self.symmetry if self.symmetry in {'none','mirror','radial','grid'} else 'none',focal_x=max(0,min(1,float(self.focal_x))),focal_y=max(0,min(1,float(self.focal_y))),focal_strength=max(0,min(1,float(self.focal_strength))),edge_bias=max(-1,min(1,float(self.edge_bias))),cluster_count=max(1,min(24,int(self.cluster_count))),cluster_strength=max(0,min(1,float(self.cluster_strength))),spacing=max(0,min(1,float(self.spacing))),jitter=max(0,min(1,float(self.jitter))),field_mode=self.field_mode if self.field_mode in {'none','noise','swirl','vortex','waves','radial'} else 'noise',field_strength=max(0,min(1.5,float(self.field_strength))),field_scale=max(.0005,min(.08,float(self.field_scale))),field_curvature=max(0,min(1,float(self.field_curvature))),field_steps=max(4,min(96,int(self.field_steps))),field_step_size=max(1,min(80,float(self.field_step_size))),noise_octaves=max(1,min(8,int(self.noise_octaves))),grid_size=max(4,min(48,int(self.grid_size))),shape_scale=max(.05,min(1.5,float(self.shape_scale))),scale_variance=max(0,min(1,float(self.scale_variance))),rotation=float(self.rotation)%360,rotation_jitter=max(0,min(math.pi,float(self.rotation_jitter))),corner_roundness=max(0,min(1,float(self.corner_roundness))),line_complexity=max(.05,min(1,float(self.line_complexity))),overlap=max(0,min(1,float(self.overlap))),organic_style=self.organic_style if self.organic_style in {'amoeba','petal','cell','droplet','leaf','blob'} else 'amoeba',organic_weight=max(0,float(self.organic_weight)),organic_lobes=max(3,min(18,int(self.organic_lobes))),organic_wobble=max(0,min(1,float(self.organic_wobble))),organic_taper=max(0,min(1,float(self.organic_taper))),organic_veins=bool(self.organic_veins),palette_mode=self.palette_mode if self.palette_mode in set(ALL_PALETTES)|{'random','pastel','lgbtq-all'} else 'random',palette_size=max(2,min(16,int(self.palette_size))),saturation=max(0,min(1.5,float(self.saturation))),contrast=max(0,min(1,float(self.contrast))),hue_jitter=max(0,min(1,float(self.hue_jitter))),opacity_min=max(.05,min(1,float(self.opacity_min))),opacity_max=max(.05,min(1,float(self.opacity_max))),color_coherence=max(0,min(1,float(self.color_coherence))),layer_count=max(1,min(8,int(self.layer_count))),depth=max(0,min(1,float(self.depth))),accent_density=max(0,min(1,float(self.accent_density))),blur=max(0,min(12,float(self.blur))),behavior=self.behavior if self.behavior in {'calm','organic','architectural','chaotic','ritual'} else 'organic',mutation=max(0,min(1,float(self.mutation))),asymmetry=max(0,min(1,float(self.asymmetry))))
    def to_dict(self): return asdict(self)
@dataclass(slots=True)
class RenderResult: image:Image.Image; svg:str; seed:str; elapsed:float

def hex_to_rgba(value):
    value=value.strip().lstrip('#'); value=''.join(c*2 for c in value) if len(value)==3 else value
    if len(value)!=6: raise ValueError(f'Invalid background color: {value!r}')
    try: rgb=tuple(int(value[i:i+2],16) for i in (0,2,4))
    except ValueError as e: raise ValueError(f'Invalid background color: {value!r}') from e
    return (*rgb,255)
def _rgb(c): return f'rgb({c[0]},{c[1]},{c[2]})'
def _rotate(points,a,cx,cy):
    ca,sa=math.cos(a),math.sin(a); return [(cx+(x-cx)*ca-(y-cy)*sa,cy+(x-cx)*sa+(y-cy)*ca) for x,y in points]

class PatternRenderer:
    FACTORS={'calm':(.55,.55,.45,.6,.55),'organic':(1,1,1,1,1),'architectural':(.12,.2,.2,.55,.35),'chaotic':(1.25,1.3,1.55,1.35,1.35),'ritual':(1.05,1.2,.6,.8,.7)}
    def generate(self,config):
        cfg=self._apply_behavior(config.normalized()); start=time.perf_counter(); seed=cfg.seed or str(random.SystemRandom().randint(0,2**31-1)); rng=random.Random(seed); bg=hex_to_rgba(cfg.background); noise=self._make_noise(seed,cfg); palette=self._palette(rng,cfg)
        image=Image.new('RGBA',(cfg.width,cfg.height),bg); draw=ImageDraw.Draw(image,'RGBA'); svg=['<?xml version="1.0" encoding="UTF-8"?>',f'<svg xmlns="http://www.w3.org/2000/svg" width="{cfg.width}" height="{cfg.height}" viewBox="0 0 {cfg.width} {cfg.height}">',f'<rect width="100%" height="100%" fill="{html.escape(cfg.background)}"/>']
        if cfg.gradient:self._gradient(draw,svg,cfg,bg)
        for layer in range(cfg.layer_count): self._draw_layer(draw,svg,cfg,random.Random(f'{seed}:layer:{layer}'),palette,noise,layer)
        self._accents(draw,svg,cfg,rng,palette); image=image.filter(ImageFilter.GaussianBlur(cfg.blur)) if cfg.blur else image; svg.append('</svg>'); return RenderResult(image,'\n'.join(svg),seed,time.perf_counter()-start)
    @classmethod
    def _apply_behavior(cls,c):
        fs,fc,rj,sv,mut=cls.FACTORS[c.behavior]; return replace(c,field_strength=min(1.5,c.field_strength*fs),field_curvature=min(1,c.field_curvature*fc),rotation_jitter=min(math.pi,c.rotation_jitter*rj),scale_variance=min(1,c.scale_variance*sv),mutation=min(1,c.mutation*mut),jitter=min(1,c.jitter*(.7+.3*mut)),cluster_strength=min(1,c.cluster_strength*(.75+.25*fs)))
    @staticmethod
    def _palette(rng,c):
        if c.palette_mode=='random': base=[(rng.randint(20,255),rng.randint(20,255),rng.randint(20,255)) for _ in range(c.palette_size)]
        elif c.palette_mode=='pastel': base=[(rng.randint(150,240),rng.randint(150,240),rng.randint(150,240)) for _ in range(c.palette_size)]
        elif c.palette_mode=='lgbtq-all': base=[ALL_LGBTQ_COLORS[i%len(ALL_LGBTQ_COLORS)] for i in range(c.palette_size)]
        else: base=[PALETTES[c.palette_mode][i%len(PALETTES[c.palette_mode])] for i in range(c.palette_size)]
        return [PatternRenderer._adjust(x,rng,c) for x in base]
    @staticmethod
    def _adjust(color,rng,c):
        r,g,b=[v/255 for v in color]; mx,mn=max(r,g,b),min(r,g,b); d=mx-mn; l=(mx+mn)/2; s=0 if d==0 else d/(1-abs(2*l-1)); s=max(0,min(1,s*c.saturation)); h=0 if d==0 else (((g-b)/d)%6 if mx==r else ((b-r)/d+2 if mx==g else (r-g)/d+4)); h=(h*60+rng.uniform(-c.hue_jitter,c.hue_jitter)*360)%360; l=max(.05,min(.95,.5+(l-.5)*(1+c.contrast))); C=(1-abs(2*l-1))*s; X=C*(1-abs((h/60)%2-1)); m=l-C/2
        if h<60:q=(C,X,0)
        elif h<120:q=(X,C,0)
        elif h<180:q=(0,C,X)
        elif h<240:q=(0,X,C)
        elif h<300:q=(X,0,C)
        else:q=(C,0,X)
        return tuple(max(0,min(255,int((v+m)*255))) for v in q)
    @staticmethod
    def _make_noise(seed,c):
        if c.field_mode=='none' or OpenSimplex is None:return None
        try:s=int(seed)
        except ValueError:s=random.Random(seed).randint(0,2**31-1)
        try:return OpenSimplex(s)
        except Exception:return None
    @staticmethod
    def _noise(x,y,n,c):
        if n is None:return 0
        total=amp=norm=0; freq=c.field_scale
        for _ in range(c.noise_octaves):
            v=n.noise2(x*freq,y*freq) if hasattr(n,'noise2') else n.noise2d(x*freq,y*freq); total+=v*amp; norm+=amp; amp*=.5; freq*=2
        return total/max(norm,1e-6)
    def _angle(self,x,y,c,n):
        nx,ny=x/c.width-.5,y/c.height-.5
        if c.field_mode=='radial':return math.atan2(ny,nx)+math.pi/2
        if c.field_mode in {'swirl','vortex'}:return math.atan2(ny,nx)+math.pi/2+math.atan2(ny,nx)*(2 if c.field_mode=='vortex' else 1)
        if c.field_mode=='waves':return math.sin(nx*8+ny*5)*math.pi+math.radians(c.rotation)
        if c.field_mode=='noise' and n is not None:return self._noise(x,y,n,c)*math.tau*(1.2+3*c.field_curvature)+math.radians(c.rotation)
        return math.radians(c.rotation)
    def _points(self,c,r):
        cols=max(2,c.grid_size); rows=max(2,int(c.grid_size*c.height/max(c.width,c.height))); sx,sy=c.width/cols,c.height/rows; clusters=[(r.uniform(0,c.width),r.uniform(0,c.height)) for _ in range(c.cluster_count)]; out=[]
        for yy in range(rows):
            for xx in range(cols):
                x=(xx+.5)*sx+r.uniform(-sx,sx)*c.jitter; y=(yy+.5)*sy+r.uniform(-sy,sy)*c.jitter
                if c.composition_mode=='focal': x+=(c.focal_x*c.width-x)*c.focal_strength*.18; y+=(c.focal_y*c.height-y)*c.focal_strength*.18
                elif c.composition_mode=='clustered':
                    cx,cy=min(clusters,key=lambda p:(p[0]-x)**2+(p[1]-y)**2); x+=(cx-x)*c.cluster_strength*.2; y+=(cy-y)*c.cluster_strength*.2
                elif c.composition_mode=='edge' and c.edge_bias<0:x+=(c.width-2*x)*abs(c.edge_bias)*.15
                elif c.composition_mode=='diagonal':z=((x+y)/(c.width+c.height)-.5)*c.width*.12; x+=z; y-=z
                out.append((x,y))
        return out
    def _draw_layer(self,d,s,c,r,p,n,layer):
        choices=[]
        for name,on,w in [('block',c.use_blocks,c.block_weight),('circle',c.use_circles,c.circle_weight),('line',c.use_lines,c.line_weight),('tri',c.use_triangles,c.triangle_weight),('organic',c.use_organic,c.organic_weight)]:
            if on and w>0: choices += [name]*max(1,int(round(w*4)))
        base=min(c.width,c.height)/max(8,c.grid_size)
        for i,(x,y) in enumerate(self._points(c,r)):
            if r.random()>c.density:continue
            size=base*c.shape_scale*(1+r.uniform(-c.scale_variance,c.scale_variance)); color=p[i%len(p)]; alpha=int(255*r.uniform(c.opacity_min,c.opacity_max)); a=math.radians(c.rotation)+r.uniform(-c.rotation_jitter,c.rotation_jitter); kind=r.choice(choices or ['organic'])
            for rx,ry in self._symmetry(x,y,c): self._shape(kind,d,s,c,r,n,rx,ry,size,a,color,alpha)
        count=max(3,int(c.grid_size*c.density*(1+c.complexity)*.75)); step=c.field_step_size*(1+layer*c.depth*.25)
        for _ in range(count):
            x,y=r.uniform(0,c.width),r.uniform(0,c.height); pts=[(x,y)]
            for __ in range(c.field_steps):
                a=self._angle(x,y,c,n); drift=step*c.field_strength*(.5+r.random()*.7); x+=math.cos(a)*drift; y+=math.sin(a)*drift
                if not(-step<x<c.width+step and -step<y<c.height+step):break
                pts.append((x,y))
            if len(pts)>2:
                col=p[r.randrange(len(p))]; al=int(255*r.uniform(c.opacity_min*.25,c.opacity_max*.5)); d.line(pts,fill=(*col,al),width=max(1,int(min(c.width,c.height)*.0015))); s.append(f'<polyline points="{" ".join(f"{x:.2f},{y:.2f}" for x,y in pts)}" fill="none" stroke="{_rgb(col)}" stroke-opacity="{al/255:.3f}"/>')
    @staticmethod
    def _symmetry(x,y,c):
        if c.symmetry=='mirror':return [(x,y),(c.width-x,y)]
        if c.symmetry=='grid':return [(x,y),(c.width-x,y),(x,c.height-y),(c.width-x,c.height-y)]
        if c.symmetry=='radial':
            cx,cy=c.width/2,c.height/2; dx,dy=x-cx,y-cy; return [(cx+dx*math.cos(a)-dy*math.sin(a),cy+dx*math.sin(a)+dy*math.cos(a)) for a in (0,math.pi/2,math.pi,3*math.pi/2)]
        return [(x,y)]
    def _shape(self,k,d,s,c,r,n,x,y,z,a,col,al):
        if k=='organic':return self._organic(d,s,c,r,n,x,y,z,a,col,al)
        if k=='circle':d.ellipse((x-z*.5,y-z*.5,x+z*.5,y+z*.5),fill=(*col,al)); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{z*.5:.1f}" fill="{_rgb(col)}" fill-opacity="{al/255:.3f}"/>'); return
        if k=='tri':pts=[(x+math.cos(a+t)*z*.62,y+math.sin(a+t)*z*.62) for t in (0,2.1,4.2)]; d.polygon(pts,fill=(*col,al)); s.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px,py in pts)}" fill="{_rgb(col)}" fill-opacity="{al/255:.3f}"/>'); return
        if k=='line':
            pts=[]
            for i in range(5):
                t=i/4; px=x+math.cos(a)*(t-.5)*z*(1+c.line_complexity*1.5); py=y+math.sin(a)*(t-.5)*z+math.sin(t*math.pi*2)*z*.15*c.complexity; pts.append((px,py))
            w=max(1,int(z*.08)); d.line(pts,fill=(*col,al),width=w,joint='curve'); s.append(f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px,py in pts)}" fill="none" stroke="{_rgb(col)}" stroke-width="{w}" stroke-opacity="{al/255:.3f}"/>'); return
        pts=_rotate([(x-z/2,y-z/2),(x+z/2,y-z/2),(x+z/2,y+z/2),(x-z/2,y+z/2)],a,x,y); d.polygon(pts,fill=(*col,al)); s.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px,py in pts)}" fill="{_rgb(col)}" fill-opacity="{al/255:.3f}"/>')
    def _organic(self,d,s,c,r,n,x,y,z,a,col,al):
        lobes=c.organic_lobes; pts=[]; scale=z*.62
        for i in range(lobes):
            t=math.tau*i/lobes; wob=1+c.organic_wobble*.28*math.sin(t*3+r.uniform(0,math.tau))
            if n is not None and c.field_mode=='noise':wob+=self._noise(x+math.cos(t)*z,y+math.sin(t)*z,n,c)*.18
            if c.organic_style=='petal':rad=scale*(.7+.25*math.cos(2*t))
            elif c.organic_style=='cell':rad=scale*(.88+.1*math.cos(6*t))
            elif c.organic_style=='droplet':rad=scale*(1-c.organic_taper*.25*(1-math.sin(t)))
            elif c.organic_style=='leaf':rad=scale*(.7+.32*math.cos(t))
            elif c.organic_style=='blob':rad=scale*(.84+.28*math.sin(2.5*t+r.random()*math.tau))
            else:rad=scale
            rad*=wob; pts.append((x+math.cos(t)*rad,y+math.sin(t)*rad))
        pts=_rotate(pts,a,x,y); d.polygon(pts,fill=(*col,al)); s.append(f'<polygon points="{" ".join(f"{px:.1f},{py:.1f}" for px,py in pts)}" fill="{_rgb(col)}" fill-opacity="{al/255:.3f}"/>')
        if c.organic_veins:
            va=max(18,int(al*.32))
            for i in (0,lobes//3,2*lobes//3):
                px,py=pts[i]; d.line((x,y,px,py),fill=(*col,va),width=max(1,int(z*.02))); s.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{_rgb(col)}" stroke-opacity="{va/255:.3f}"/>')
    @staticmethod
    def _accents(d,s,c,r,p):
        count=int(80*c.accent_density*(c.width*c.height/max(1,min(c.width,c.height)**2)))
        for _ in range(count):
            x,y=r.uniform(0,c.width),r.uniform(0,c.height); q=r.uniform(.5,3)*(1+c.depth); col=p[r.randrange(len(p))]; al=r.randint(40,180); d.ellipse((x-q,y-q,x+q,y+q),fill=(*col,al)); s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{q:.1f}" fill="{_rgb(col)}" fill-opacity="{al/255:.3f}"/>')
    @staticmethod
    def _gradient(d,s,c,bg):s.append('<defs><linearGradient id="bgGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#fff" stop-opacity=".12"/><stop offset="100%" stop-color="#000" stop-opacity=".10"/></linearGradient></defs><rect width="100%" height="100%" fill="url(#bgGradient)"/>')
