MMUL_ANIMS = mmul_0naive.pdf mmul_1trans.pdf mmul_2trans_block.pdf	\
	     mmul_3trans_block_l1.pdf mmul_4trans_block_2level.pdf
MMUL_VIDEOS=$(MMUL_ANIMS:%.pdf=%.mp4)

all: $(MMUL_ANIMS) $(MMUL_VIDEOS)

$(MMUL_ANIMS): matrix_mul.py
	./$< -o $@ $(ANIM_FLAGS-$(basename $@))

$(MMUL_VIDEOS): matrix_mul.py
	./$< -o $@ $(ANIM_FLAGS-$(basename $@))

clean:
	rm -rf $(MMUL_ANIMS) $(MMUL_VIDEOS)

ANIM_FLAGS-mmul_0naive = --title "Naive"
ANIM_FLAGS-mmul_1trans = --title "B transposed" --transpose
ANIM_FLAGS-mmul_2trans_block = --title "Tiled, B transposed" --transpose --block1=4
ANIM_FLAGS-mmul_3trans_block_l1 = --title "Tiled, B transposed" --transpose --block1=4 --L1=2
ANIM_FLAGS-mmul_4trans_block_2level = --title "2-level tiled, B transposed" --transpose --block1=2 --block2=4 --L1=2
