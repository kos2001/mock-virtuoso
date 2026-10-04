scalegrid 1 2
source /Volumes/T9-Workspace/gitspace/virtuso_bridge/mock-virtuoso/.tools/pdks/ciel/sky130/versions/0c1df35fd535299ea1ef74d1e9e15dedaeb34c32/sky130A/libs.tech/magic/sky130A.tcl
snap internal
load n1
box values 0 0 0 0
set pars [dict merge [sky130::sky130_fd_pr__nfet_01v8_defaults] {w 1 l 0.15 doports 1}]
sky130::sky130_fd_pr__nfet_01v8_draw $pars
save n1
gds write n1.gds
load n2
box values 0 0 0 0
set pars [dict merge [sky130::sky130_fd_pr__nfet_01v8_defaults] {w 2 l 0.15 doports 1}]
sky130::sky130_fd_pr__nfet_01v8_draw $pars
save n2
gds write n2.gds
load n4
box values 0 0 0 0
set pars [dict merge [sky130::sky130_fd_pr__nfet_01v8_defaults] {w 4 l 0.15 doports 1}]
sky130::sky130_fd_pr__nfet_01v8_draw $pars
save n4
gds write n4.gds
load p1
box values 0 0 0 0
set pars [dict merge [sky130::sky130_fd_pr__pfet_01v8_defaults] {w 1 l 0.15 doports 1}]
sky130::sky130_fd_pr__pfet_01v8_draw $pars
save p1
gds write p1.gds
quit -noprompt
