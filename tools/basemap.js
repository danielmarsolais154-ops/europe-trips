const topo = require('topojson-client');
const w = require('world-atlas/countries-50m.json');
const fc = topo.feature(w, w.objects.countries);
const B = [-32, 30, 60, 73];
const r = x => Math.round(x * 100) / 100;
function inBox(ring){ return ring.some(([x,y]) => x >= B[0] && x <= B[2] && y >= B[1] && y <= B[3]); }
const out = [];
for (const f of fc.features){
  const g = f.geometry; if (!g) continue;
  const polys = g.type === 'Polygon' ? [g.coordinates] : g.coordinates;
  const keep = polys.filter(p => inBox(p[0]) && !p[0].some(([x]) => x < -40 || x > 179)).map(p => p.map(ring => {
    const o = []; let last;
    for (const [x,y] of ring){ const pt = [r(x), r(y)]; if (!last || pt[0] !== last[0] || pt[1] !== last[1]) o.push(pt); last = pt; }
    return o;
  }).filter(ring => ring.length >= 4));
  if (keep.length) out.push({type:'Feature', properties:{n:f.properties.name}, geometry:{type:'MultiPolygon', coordinates:keep}});
}
require('fs').writeFileSync('/home/claude/app/src/basemap.json', JSON.stringify({type:'FeatureCollection', features:out}));
console.log(out.length, out.map(f=>f.properties.n).slice(0,80).join(', '));
