
echo """# Extract Annotated Patches

To build the singularity image do:

\`\`\`
singularity build --remote extract_annotated_patches.sif Singularityfile.def
\`\`\`

Here's an example of the setup you can use:

\`experiment.yaml\`

\`\`\`
extract_annotated_patches:
    patch_location: /projects/ovcare/classification/cchen/ml/data/test_ec/patches
    use-directory:
        slide_location: /projects/ovcare/classification/cchen/ml/data/test_ec/slides
        use-annotation:
            annotation_location: /projects/ovcare/classification/cchen/ml/data/test_ec/annotations
            slide_coords_location: /projects/ovcare/classification/cchen/ml/data/test_ec/slide_coor
ds.json
            patch_size: 1024
            resize_size: [256]
\`\`\`

In the SH file, you should bind the path to the slides if the slides in your slides directory specified by \`--slide_location\` is symlinked.

\`\`\`
singularity run \
    -B /projects/ovcare/classification/cchen \
    -B /projects/ovcare/WSI \
    extract_annotated_patches.sif \
    from-experiment-manifest /path/to/experiment.yaml \

## Usage
\`\`\`

\`\`\`""" > README.md

python app.py -h >> README.md
echo >> README.md
python app.py from-experiment-manifest -h >> README.md
echo >> README.md
python app.py from-arguments -h >> README.md
echo >> README.md
echo "use-manifest is not implemented yet" >> README.md
echo >> README.md
python app.py from-arguments use-directory -h >> README.md
echo >> README.md
python app.py from-arguments use-directory use-slide-coords -h >> README.md
echo >> README.md
python app.py from-arguments use-directory use-annotation -h >> README.md
echo """\`\`\`
""" >> README.md

