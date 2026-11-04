typedef unsigned char u8;
typedef unsigned int u32;
__attribute__((noinline)) static unsigned distance(u32 p,u32 b) {
 unsigned d=0;
 for(unsigned i=0;i<3;i++) {int q=(int)((p>>(8*i))&255)-(int)((b>>(8*i))&255);unsigned a=q<0?-q:q;if(a>d)d=a;}
 unsigned pl=((p&255)*54+((p>>8)&255)*183+((p>>16)&255)*19)>>8;
 unsigned bl=((b&255)*54+((b>>8)&255)*183+((b>>16)&255)*19)>>8;
 unsigned lum=pl>bl?pl-bl:bl-pl;if(lum>128)lum=128;
 return d|((160+lum*95/128)<<8);
}
static u32 color(u8 *p) {
 u32 c=0;
 for(unsigned j=0;j<3;j++){unsigned v=(unsigned)p[j]*255/p[3];if(v>255)v=255;c|=v<<(8*j);}
 return c;
}
__attribute__((noinline)) static u32 blend(u32 a,u32 b,unsigned t,unsigned n) {
 u32 v=0;
 for(unsigned j=0;j<3;j++)v|=(( ((a>>(8*j))&255)*(n-t)+((b>>(8*j))&255)*t)/n)<<(8*j);
 return v;
}
__attribute__((noinline)) static void finish(u8 *p,unsigned a,unsigned intensity,unsigned x,unsigned y,unsigned w,unsigned remove) {
 unsigned edge=w/16,inset=x<y?x:y,z=w-1-x;if(z<inset)inset=z;z=w-1-y;if(z<inset)inset=z;
 if(remove&&inset<edge)a=a*inset/edge;
 a=a*220/255;
 unsigned r=w/4,dx=x<w-1-x?x:w-1-x,dy=y<w-1-y?y:w-1-y;
 unsigned coverage=255;
 if(dx<r&&dy<r){
  unsigned cx=2*(r-dx)-1,cy=2*(r-dy)-1,q=cx*cx+cy*cy;
  unsigned inner=(2*r-1)*(2*r-1),outer=(2*r+1)*(2*r+1);
  if(q>=outer)coverage=0;else if(q>inner)coverage=(outer-q)*255/(outer-inner);
 }
 a=a*coverage/255;
 unsigned base=18*coverage/255;
 if(remove)base=base*p[3]/255;
 unsigned b=base*(255-a)/255,total=a+b;
 unsigned value=total?(a*intensity+b*255)/total:0;
 p[0]=p[1]=p[2]=value;p[3]=total;
}
__attribute__((visibility("hidden"))) void clear_content(u8 *data,unsigned len) {
 unsigned pixels=len/4,w=1;
 while(w*w<pixels&&w<=512)w++;
 if(w*w!=pixels||w<24||w>512)return;
 unsigned m=w/16;
 unsigned plate=0;
 for(unsigned i=0;i<4;i++){unsigned x=i<2?w/2:(i==2?m:w-1-m);unsigned y=i<2?(i? w-1-m:m):w/2;if(data[4*(y*w+x)+3]>180)plate++;}
 plate=plate>=3;
 u8 *a0=data+4*((w/4)*w+m),*a1=data+4*((w/4)*w+w-1-m);
 u8 *b0=data+4*((3*w/4)*w+m),*b1=data+4*((3*w/4)*w+w-1-m);
 plate=plate&&a0[3]>180&&a1[3]>180&&b0[3]>180&&b1[3]>180;
 u32 lt=plate?color(a0):0,rt=plate?color(a1):0,lb=plate?color(b0):0,rb=plate?color(b1):0;
 for(unsigned y=0;y<w;y++) {
  u8 *row=data+4*y*w;
  unsigned remove=plate;
  unsigned v=y<w/4?0:y>3*w/4?w/2:y-w/4;
  u32 left=blend(lt,lb,v,w/2),right=blend(rt,rb,v,w/2);
  for(unsigned x=0;x<w;x++) {
   u8 *p=row+4*x;unsigned a=p[3],intensity=255;
   if(remove&&a){
    unsigned t=x<m?0:x>w-1-m?w-1-2*m:x-m;
    u32 bg=blend(left,right,t,w-1-2*m);
    unsigned metrics=distance(color(p),bg);
    unsigned d=metrics&255;intensity=metrics>>8;
    unsigned contrast=d>36?d-36:0;if(contrast>160)contrast=160;
    a=a*contrast/160;
   }
   finish(p,a,intensity,x,y,w,remove);
  }
 }
}
