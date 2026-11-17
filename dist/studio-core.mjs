export const HOME=[0,-.45,0,-2.05,0,1.6,.7854];
export const TRAY=[.48,.24,.382];
export function sceneFromSeed(seed,condition='normal'){
 let s=seed>>>0;const rand=()=>((s=(1664525*s+1013904223)>>>0)/4294967296);
 for(let i=0;i<8;i++)rand();
 const p=[.43+.08*rand(),-.05+.07*rand(),.383];if(condition==='unreachable')p[0]=.95;return p;
}
export function solve(a,b){
 const m=a.map((r,i)=>[...r,b[i]]),n=b.length;
 for(let i=0;i<n;i++){
  let k=i;for(let j=i+1;j<n;j++)if(Math.abs(m[j][i])>Math.abs(m[k][i]))k=j;
  [m[k],m[i]]=[m[i],m[k]];const d=m[i][i];if(Math.abs(d)<1e-12)throw Error('Singular IK system');
  for(let j=i;j<=n;j++)m[i][j]/=d;
  for(let j=0;j<n;j++)if(j!==i){const f=m[j][i];for(let k=i;k<=n;k++)m[j][k]-=f*m[i][k];}
 }
 return m.map(r=>r[n]);
}
export function judgePlacement(p,width,collision){return Math.abs(p[0]-.48)<.065&&Math.abs(p[1]-.24)<.06&&p[2]>.37&&p[2]<.42&&width>.065&&!collision;}
const percentile=(xs,q)=>{xs.sort((a,b)=>a-b);const i=(xs.length-1)*q,f=Math.floor(i);return xs[f]+(xs[Math.min(f+1,xs.length-1)]-xs[f])*(i-f);};
// Same HSV gate, 3x3 opening and largest connected component as Python. Inputs
// contain rendered sensor pixels and calibration, never simulator target poses.
export function estimateRGBD(rgba,depth,n,fovy,pos,rot){
 const raw=new Uint8Array(n*n),erode=new Uint8Array(n*n),mask=new Uint8Array(n*n);
 for(let i=0;i<n*n;i++){
  const r=rgba[4*i],g=rgba[4*i+1],b=rgba[4*i+2],v=Math.max(r,g,b),mn=Math.min(r,g,b),d=v-mn;
  let h=d===0?0:v===r?((g-b)/d)%6:v===g?(b-r)/d+2:(r-g)/d+4;h=(h*30+180)%180;
  if((h<12||h>170)&&255*d/(v||1)>140&&v>60)raw[i]=1;
 }
 for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){let good=1;for(let j=-1;j<=1;j++)for(let k=-1;k<=1;k++)good&=raw[(y+j)*n+x+k];erode[y*n+x]=good;}
 for(let y=1;y<n-1;y++)for(let x=1;x<n-1;x++){let any=0;for(let j=-1;j<=1;j++)for(let k=-1;k<=1;k++)any|=erode[(y+j)*n+x+k];mask[y*n+x]=any;}
 let best=[];const seen=new Uint8Array(n*n);
 for(let i=0;i<n*n;i++)if(mask[i]&&!seen[i]){
  const queue=[i];seen[i]=1;
  for(let k=0;k<queue.length;k++){const v=queue[k],x=v%n,y=Math.floor(v/n);for(let j=-1;j<=1;j++)for(let dx=-1;dx<=1;dx++){
   const xx=x+dx,yy=y+j,z=yy*n+xx;if(xx>=0&&xx<n&&yy>=0&&yy<n&&mask[z]&&!seen[z]){seen[z]=1;queue.push(z);}
  }}if(queue.length>best.length)best=queue;
 }
 if(best.length<12)return null;
 const f=n/(2*Math.tan(fovy*Math.PI/360)),points=[[],[],[]];let minx=n,miny=n,maxx=0,maxy=0;
 for(const i of best){const x=i%n,y=Math.floor(i/n),z=depth[i];if(!Number.isFinite(z)||z<=0||z>=3)continue;
  const v=[(x+.5-n/2)*z/f,-(y+.5-n/2)*z/f,-z];
  for(let k=0;k<3;k++)points[k].push(pos[k]+rot[3*k]*v[0]+rot[3*k+1]*v[1]+rot[3*k+2]*v[2]);
  minx=Math.min(minx,x);miny=Math.min(miny,y);maxx=Math.max(maxx,x);maxy=Math.max(maxy,y);
 }
 if(points[0].length<12)return null;
 return {position:[(percentile(points[0],.03)+percentile(points[0],.97))/2,(percentile(points[1],.03)+percentile(points[1],.97))/2,.382],pixels:best.length,bbox:[minx,miny,maxx,maxy]};
}
