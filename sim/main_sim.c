#include "aka_hal.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char**argv){
  if(argc<2){fprintf(stderr,"usage: %s <script.py>\n",argv[0]);return 2;}
  size_t heap=1024*1024; void*p=malloc(heap);
  if(!p){fprintf(stderr,"oom\n");return 1;}
  aka_boot_init(p,heap);
  aka_boot_exec(argv[1]);
  return 0;
}
