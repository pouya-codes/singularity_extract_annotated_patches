# Extract Annotated Patches

To build the singularity image do:

```
singularity build --remote extract_annotated_patches.sif Singularityfile.def
```

Here's an example of the setup you can use:

`experiment.yaml`

```
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
```

In the SH file, you should bind the path to the slides if the slides in your slides directory specified by `--slide_location` is symlinked.

```
singularity run     -B /projects/ovcare/classification/cchen     -B /projects/ovcare/WSI     extract_annotated_patches.sif     from-experiment-manifest /path/to/experiment.yaml 
```

## Usage

```
usage: app.py [-h] {from-experiment-manifest,from-arguments} ...

Extract annotated patches.

positional arguments:
  {from-experiment-manifest,from-arguments}
                        Choose whether to use arguments from experiment
                        manifest or from commandline
    from-experiment-manifest
                        Use experiment manifest
    from-arguments      Use arguments

optional arguments:
  -h, --help            show this help message and exit

usage: app.py from-experiment-manifest [-h] [--component_id COMPONENT_ID]
                                       experiment_manifest_location

positional arguments:
  experiment_manifest_location

optional arguments:
  -h, --help            show this help message and exit
  --component_id COMPONENT_ID

usage: app.py from-arguments [-h] --patch_location PATCH_LOCATION [--is_tumor]
                             [--seed SEED]
                             [--num_patch_workers NUM_PATCH_WORKERS]
                             {use-manifest,use-directory} ...

positional arguments:
  {use-manifest,use-directory}
                        Specify how to load slides to extract. There are 2
                        ways of extracting slides: by manifest and by
                        directory.
    use-manifest        Use manifest file to locate slides. A manifest JSON
                        file contains keys 'patients', and optionally
                        'patient_regex' which is the regex string used to
                        extract the patient from the slide name. The key
                        'patients' which is a dictionary where each key is a
                        patient ID and value is a list of slide paths for the
                        slides corresponding to the patient. { patient_regex:
                        str|None, patients: { [patient ID]: [str, ...], ... }
                        }
    use-directory       Use a rootdir to locate slides. It is expected that
                        slide paths have the structure
                        '/path/to/rootdir/slide_pattern/slide_name.extension'
                        where slide_pattern is usually 'subtype'. Patient IDs
                        are extrapolated from slide_name using known,
                        hardcoded regex.

optional arguments:
  -h, --help            show this help message and exit
  --is_tumor            Only extract tumor patches. Default extracts tumor and
                        normal patches.
  --seed SEED           Seed for random shuffle.
  --num_patch_workers NUM_PATCH_WORKERS
                        Number of worker processes to multi-process patch
                        extraction. Default sets the number of worker
                        processes to the number of CPU processes.

required arguments:
  --patch_location PATCH_LOCATION
                        Path to root directory to extract patches into.

use-manifest is not implemented yet

usage: app.py from-arguments use-directory [-h] --slide_location
                                           SLIDE_LOCATION
                                           [--slide_pattern SLIDE_PATTERN]
                                           {use-slide-coords,use-annotation}
                                           ...

positional arguments:
  {use-slide-coords,use-annotation}
                        Specify which coordinates in the slides to extract.
                        There are 2 ways of extracting patches: by slide_cords
                        and by annotation.
    use-slide-coords    Specify patches to extract using slide coordinates. A
                        slide coords JSON file containing keys 'patch_size'
                        and 'coords'. The key 'patch_size' gives the pixel
                        width, height of the patch. Coordinates are a list of
                        size 2 lists of numbers representing the x, y pixel
                        coordinates. The [x, y] list represents the
                        coordinates of the top left corner of the patch_size *
                        patch_size extracted patch. Coordinates are indexed by
                        slide name for the slide the patches are from, and
                        annotation the patches are labeled with. { patch_size:
                        int, coords: { [slide name]: { [label]: [ [int|float,
                        int|float], ... ], ... }, ... } }
    use-annotation      Specify patches to extract by annotation. If a slide
                        is named 'VOA-1823A' then the annotation file for that
                        slide is a text file named 'VOA-1823A.txt' with each
                        line containing (i.e.): Tumor [Point: 84332.8046875,
                        68421.28125, Point: 84332.8046875, 68421.28125,...]
                        Stroma [...]

optional arguments:
  -h, --help            show this help message and exit
  --slide_pattern SLIDE_PATTERN
                        '/' separated words describing the directory structure
                        of the slide paths. Normally slides paths look like
                        /path/to/slide/rootdir/subtype/slide.svs and if slide
                        paths are /path/to/slide/rootdir/slide.svs then simply
                        pass ''.

required arguments:
  --slide_location SLIDE_LOCATION
                        Path to slide rootdir.

usage: app.py from-arguments use-directory use-slide-coords
       [-h] --slide_coords_location SLIDE_COORDS_LOCATION

optional arguments:
  -h, --help            show this help message and exit

required arguments:
  --slide_coords_location SLIDE_COORDS_LOCATION
                        Path to slide coords JSON file.

usage: app.py from-arguments use-directory use-annotation [-h]
                                                          --annotation_location
                                                          ANNOTATION_LOCATION
                                                          --slide_coords_location
                                                          SLIDE_COORDS_LOCATION
                                                          [--patch_size PATCH_SIZE]
                                                          [--resize_sizes RESIZE_SIZES [RESIZE_SIZES ...]]
                                                          [--max_slide_patches MAX_SLIDE_PATCHES]

optional arguments:
  -h, --help            show this help message and exit
  --patch_size PATCH_SIZE
                        Patch size in pixels to extract from slide.
  --resize_sizes RESIZE_SIZES [RESIZE_SIZES ...]
                        List of patch sizes in pixels to resize the extracted
                        patches and save. Each size should be at most
                        patch_size. Default simply saves the extracted patch.
  --max_slide_patches MAX_SLIDE_PATCHES
                        Select at most max_slide_patches number of patches
                        from each slide.

required arguments:
  --annotation_location ANNOTATION_LOCATION
                        Path to immediate directory containing slide's
                        annotation TXTs.
  --slide_coords_location SLIDE_COORDS_LOCATION
                        Path to slide coords JSON file to save extracted patch
                        coordinates.
```

