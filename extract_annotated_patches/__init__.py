# Built-ins
import os
import os.path
import logging
import json
import multiprocessing as mp
from PIL import Image
import math
# Libraries
import psutil
from tqdm import tqdm
import h5py
import numpy as np
from openslide import OpenSlide
from sklearn.cluster import KMeans
from collections import defaultdict


# Modules
import submodule_utils as utils
from submodule_utils.thumbnail import PlotThumbnail
from submodule_utils.subtype_enum import BinaryEnum
from submodule_utils.mixins import OutputMixin
from submodule_utils.metadata.annotation import GroovyAnnotation
from submodule_utils.metadata.tissue_mask import TissueMask
from submodule_utils.metadata.slide_coords import (
        SlideCoordsMetadata, CoordsMetadata)
from submodule_utils.image.extract import (
        SlideCoordsExtractor, SlidePatchExtractor)
import submodule_utils.image.preprocess as preprocess

logger = logging.getLogger('extract_annotated_patches')

default_component_id = "extract_annotated_patches"
default_seed = 256
default_slide_pattern = 'subtype'
default_patch_size = 1024
default_evaluation_size = int(default_patch_size/8) # 5x




class AnnotatedPatchesExtractor(OutputMixin):
    """Extracted annotated patches

    Attributes
    ----------
    slide_coords : SlideCoordsMetadata
        Metadata object containing slide coords to use in extracting patches.
        When 'use-annotation' is set, we DO NOT set slide_coords. Instead each child process creates a SlideCoordsMetadata and then uses multiprocess.Pipe to send them to the parent process to merge.
    """
    FULL_MAGNIFICATION = 40
    MAX_N_PROCESS = 200

    def get_magnification(self, resize_size):
        return int(float(resize_size) * float(self.FULL_MAGNIFICATION) \
            / float(self.patch_size))

    @property
    def should_use_manifest(self):
        return self.load_method == 'use-manifest'

    @property
    def should_use_directory(self):
        return self.load_method == 'use-directory'

    @property
    def should_use_hd5_files(self):
        return self.load_method == 'from-hd5-files'

    @property
    def should_use_slide_coords(self):
        return self.extract_method == 'use-slide-coords' if hasattr(self, 'extract_method') else False

    @property
    def should_use_annotation(self):
        return self.extract_method == 'use-annotation' if hasattr(self, 'extract_method') else False

    @property
    def should_use_entire_slide(self):
        return self.extract_method == 'use-entire-slide' if hasattr(self, 'extract_method') else False

    @property
    def should_use_mosaic(self):
        return self.extract_method == 'use-mosaic' if hasattr(self, 'extract_method') else False

    def get_slide_paths(self):
        """Get paths of slides that should be extracted.
        """
        if self.should_use_manifest:
            return self.manifest['slide_path']
        elif self.should_use_directory or self.should_use_hd5_files:
            return utils.get_paths(self.slide_location, self.slide_pattern,
                    extensions=['tiff', 'tif', 'svs', 'scn'])
        else:
            raise NotImplementedError()

    def load_slide_tissue_mask(self):
        """Load tissue masks from slide names.
        """
        if self.should_use_manifest:
            generator = self.manifest['mask_path']
        elif self.should_use_directory:
            generator = os.listdir(self.mask_location)
        else:
            raise NotImplementedError()
        # if it is .png, we need to know the true size of slide
        # since the mask is scale down version of it
        list_slides = self.get_slide_paths()
        slide_tissue_mask = {}
        for file in generator:
            if file.endswith(".png") or file.endswith(".txt") or file.endswith(".svs"):
                slide_name = utils.path_to_filename(file)
                slide_path = utils.find_slide_path(list_slides, slide_name)
                if slide_path is None: # the path to that slide was not found
                    continue
                else:
                    os_slide = OpenSlide(slide_path)
                    slide_size = os_slide.dimensions
                if self.should_use_manifest:
                    filepath = file
                else:
                    filepath = os.path.join(self.mask_location, file)
                slide_tissue_mask[slide_name] = TissueMask(filepath, 0.4, self.patch_size,
                                                           slide_size)
        return slide_tissue_mask


    def load_slide_annotation_lookup(self):
        """Load annotation TXT files from annotation_location and set up lookup table for slide region annotations from slide names.

        Returns
        -------
        dict of str: GroovyAnnotation
            Lookup table for slide region annotations from slide names.
        """
        if self.should_use_manifest:
            if 'annotation_path' not in self.manifest:
                raise ValueError("There is no column named annotation_path in the manifest file.")
            generator = self.manifest['annotation_path']
        elif self.should_use_directory:
            generator = os.listdir(self.annotation_location)
        else:
            raise NotImplementedError()

        slide_annotation = {}
        for file in generator:
            if file.endswith(".txt"):
                slide_name = utils.path_to_filename(file)
                if self.should_use_manifest:
                    filepath = file
                else:
                    filepath = os.path.join(self.annotation_location, file)
                slide_annotation[slide_name] = GroovyAnnotation(filepath, self.annotation_overlap,
                                                                self.patch_size, self.is_TMA, logger)
        return slide_annotation

    def __init__(self, config):
        """
        TODO: fix import-annotations and export-annotations
        """
        self.hd5_location = config.hd5_location
        self.seed = config.seed
        self.load_method = config.load_method
        self.store_thumbnail = config.store_thumbnail
        if self.should_use_manifest:
            self.manifest = utils.read_manifest(config.manifest_location)
            self.patch_location = config.patch_location
            self.slide_idx = config.slide_idx
            self.store_extracted_patches = config.store_extracted_patches
            self.slide_coords_location = config.slide_coords_location
            self.extract_method = config.extract_method
            self.slide_coords_location = config.slide_coords_location
        elif self.should_use_hd5_files:
            self.slide_location = config.slide_location
            self.slide_pattern = utils.create_patch_pattern(config.slide_pattern)
            self.slide_idx = config.slide_idx
            self.resize = config.resize
            self.max_num_patches = config.max_num_patches
        elif self.should_use_directory:
            self.slide_location = config.slide_location
            self.slide_pattern = utils.create_patch_pattern(config.slide_pattern)
            self.slide_idx = config.slide_idx
            self.extract_method = config.extract_method
            self.patch_location = config.patch_location
            self.slide_coords_location = config.slide_coords_location
            self.store_extracted_patches = config.store_extracted_patches
            self.store_extracted_patches_as_hd5 = config.store_extracted_patches_as_hd5
            self.mask_location = config.mask_location
        else:
            raise NotImplementedError(f"Load method {self.load_method} not implemented")

        if self.should_use_directory or self.should_use_manifest:
            if self.should_use_annotation:
                self.annotation_location = config.annotation_location
                self.annotation_overlap = config.annotation_overlap
                self.patch_overlap = config.patch_overlap
                self.patch_size = config.patch_size
                self.stride = config.stride
                self.is_tumor = config.is_tumor
                self.is_TMA = config.is_TMA
                self.slide_annotation = self.load_slide_annotation_lookup()
                self.resize_sizes = config.resize_sizes
                self.__resize_sizes = config.resize_sizes
                self.max_slide_patches = config.max_slide_patches
                self.use_radius = config.use_radius
                self.radius = config.radius
            elif self.should_use_entire_slide:
                self.stride = config.stride
                self.patch_size = config.patch_size
                self.resize_sizes = config.resize_sizes
                self.max_slide_patches = config.max_slide_patches
                self.use_radius = config.use_radius
                self.radius = config.radius
            elif self.should_use_mosaic:
                self.stride = config.stride
                self.patch_size = config.patch_size
                self.evaluation_size = config.evaluation_size
                self.resize_sizes = config.resize_sizes
                self.n_clusters = config.n_clusters
                self.percentage = config.percentage
                self.use_radius = config.use_radius
                self.radius = config.radius
            elif self.should_use_slide_coords:
                self.slide_coords_metadata = SlideCoordsMetadata.load(self.slide_coords_location)
                self.patch_size = self.slide_coords_metadata.patch_size
                self.resize_sizes = self.slide_coords_metadata.resize_sizes
            else:
                raise NotImplementedError(f"Extract method {self.extract_method} not implemented")

            if self.should_use_directory and self.mask_location is not None:
                self.use_mask = True
                self.mask = self.load_slide_tissue_mask()
            elif self.should_use_manifest and 'mask_path' in self.manifest:
                self.use_mask = True
                self.mask = self.load_slide_tissue_mask()
            else:
                self.use_mask = False

            if not self.resize_sizes:
                self.resize_sizes = [self.patch_size]

        self.slide_paths = self.get_slide_paths()
        if config.num_patch_workers:
            self.n_process = config.num_patch_workers
        else:
            self.n_process = psutil.cpu_count()

    def print_parameters(self):
        """
        TODO: finish this.
        TODO: remember to print counts of patches, etc.
        """
        pass

    def extract_patch_by_hd5_files(self, slide_path, class_size_to_patch_path):
        try:
            slide_name = utils.path_to_filename(slide_path)
            hd5_file_location = os.path.join(self.hd5_location, f"{slide_name}.h5")
            paths, patch_size = utils.open_hd5_file(hd5_file_location)
            os_slide = OpenSlide(slide_path)
            counter = 0
            for path in paths:
                x, y = os.path.splitext(os.path.basename(path))[0].split('_')
                resize_size = int(utils.get_patchsize_by_patch_path(path))
                if self.resize is not None and resize_size not in self.resize:
                    continue
                os.makedirs(os.path.dirname(path), exist_ok=True)
                patch = preprocess.extract(os_slide, int(x), int(y), patch_size)
                if counter >= self.max_num_patches: break
                counter += 1
                if patch_size==resize_size:
                    patch.save(path)
                else:
                    resized_patch = preprocess.resize(patch, resize_size)
                    resized_patch.save(path)
            logger.info(f"{counter} patches are selected from {slide_name}.")
            if self.store_thumbnail:
                PlotThumbnail(slide_name, os_slide, hd5_file_location, None)
        except Exception as e:
            logger.error(f"could not process f{hd5_file_location}\n{e}")

    def extract_patch_by_slide_coords(self, slide_path, class_size_to_patch_path):
        slide_name = utils.path_to_filename(slide_path)
        os_slide = OpenSlide(slide_path)

        for data in self.slide_coords_metadata.get_slide(slide_name):
            label, coord = data
            x, y = coord
            if self.is_tumor and label != BinaryEnum(1).name:
                """Skip non-tumor patch if is_tumor is set.
                """
                continue

            patch = preprocess.extract(os_slide, x, y, self.patch_size)
            save_location = os.path.join(patch_path, f"{x}_{y}.png")
            for resize_size in self.resize_sizes:
                patch_path = class_size_to_patch_path[label][resize_size]
                if resize_size == self.patch_size:
                    patch.save(save_location)
                else:
                    resized_patch = preprocess.resize(patch, resize_size)
                    resized_patch.save(save_location)

    def extract_(self, os_slide, slide_name, label, paths, x, y, class_size_to_patch_path,
                 is_TMA=False, check_background=False):
        """ Had to ceate this function for radius patch extraction
        """
        patch = preprocess.extract(os_slide, x, y, self.patch_size, is_TMA=is_TMA)
        ndpatch = utils.image.preprocess.pillow_image_to_ndarray(patch)
        check = utils.image.preprocess.check_luminance(ndpatch)
        if check_background:
            return check
        if check:
            for resize_size in self.resize_sizes:
                patch_path = os.path.join(class_size_to_patch_path[label][resize_size], f"{x}_{y}.png")
                paths.append(patch_path)
                # save as PNG
                if self.store_extracted_patches:
                    if resize_size == self.patch_size:
                        patch.save(os.path.join(patch_path))
                    else:
                        resized_patch = preprocess.resize(patch, resize_size)
                        resized_patch.save(os.path.join(patch_path))
                # save as a HD5 whose name is same as the image
                elif self.store_extracted_patches_as_hd5:
                    hd5_name = os.path.join(self.patch_location, f"{slide_name}.h5")
                    hf = h5py.File(hd5_name, 'a')
                    patch_path = os.path.join(class_size_to_patch_path[label][resize_size], f"{x}_{y}.png")
                    patch_path = patch_path[len(self.patch_location)+1:]
                    if resize_size != self.patch_size:
                        patch = preprocess.resize(patch, resize_size)
                    hf.create_dataset(patch_path, data=patch, chunks=True,
                                      compression="gzip", compression_opts=9)
                    hf.close()
        return paths, check

    def check_label(self, slide_name, x, y):
        label = self.slide_annotation[slide_name].points_to_label(
                np.array([[x, y],
                    [x, y+self.patch_size],
                    [x+self.patch_size, y+self.patch_size],
                    [x+self.patch_size, y]]))
        if not label:
            """Skip unlabeled patches
            """
            return label, False
        if self.is_tumor and BinaryEnum(1).name not in label:
            """Skip non-tumor patch if is_tumor is set.
            """
            return label, False
        return label, True

    def check_tissue(self, slide_name, x, y):
        label = self.mask[slide_name].points_to_label(
                np.array([[x, y],
                    [x, y+self.patch_size],
                    [x+self.patch_size, y+self.patch_size],
                    [x+self.patch_size, y]]))
        if not label:
            return False
        return True

    def extract_patch_by_annotation(self, slide_path,
            class_size_to_patch_path, send_end):
        """Extracts patches using the steps:
         1. Moves a sliding, non-overlaping window to extract each patch to Pillow patch.
         2. Converts patch to ndarray ndpatch and skips to next patch if background

        Parameters
        ----------
        slide_path : str
            Path of slide to extract patch

        class_size_to_patch_path : dict
            To get the patch path a store evaluated patch using evaluated label name and patch size as keys

        send_end : multiprocessing.connection.Connection
            Connection to send recorded coords metadata of a slide to parent.
        """
        slide_name = utils.path_to_filename(slide_path)
        if not self.is_TMA:
            os_slide = OpenSlide(slide_path)
        else:
            os_slide = Image.open(slide_path).convert('RGB')
            os_slide = preprocess.expand(os_slide, self.patch_size, self.annotation_overlap)
        coords = CoordsMetadata(slide_name, patch_size=self.patch_size)
        num_extracted = 0
        extracted_coordinates = defaultdict(list)
        paths = []
        hd5_file_path = os.path.join(self.hd5_location, f"{slide_name}.h5")
        shuffle_coordinate = True if self.max_slide_patches is not None else False
        for data in SlideCoordsExtractor(os_slide, self.patch_size, self.patch_overlap,
                                         shuffle=shuffle_coordinate, seed=self.seed,
                                         is_TMA=self.is_TMA, stride=self.stride):
            if self.max_slide_patches is not None and num_extracted >= self.max_slide_patches:
                """Stop extracting patches once we have reach the max number of them for this slide.
                """
                break
            tile_x, tile_y, x, y = data
            if self.use_mask and slide_name in self.mask:
                check_tissue = self.check_tissue(slide_name, x, y)
                if not check_tissue:
                    continue
            label, is_label = self.check_label(slide_name, x, y)
            if not is_label:
                continue

            if self.use_radius:
                stride = int((1-self.patch_overlap)*self.patch_size)
                size   = os_slide.dimensions if not self.is_TMA else os_slide.size
                Coords = utils.get_circular_coordinates(self.radius, x, y, stride,
                                            size, self.patch_size)
            else:
                Coords = [(x, y)]
            # check main image; if it is background, skip it
            check = self.extract_(os_slide, slide_name, label, paths, x, y, class_size_to_patch_path,
                                  is_TMA=self.is_TMA, check_background=True)
            if not check:
                continue
            for coord in Coords:
                x_, y_ = coord
                if self.use_mask and slide_name in self.mask:
                    check_tissue = self.check_tissue(slide_name, x_, y_)
                    if not check_tissue:
                        continue
                labels, is_label = self.check_label(slide_name, x_, y_)
                if not is_label:
                    continue
                for label in labels:
                    if (x_, y_) in extracted_coordinates[label]: # it has been previously extracted (usefull for radius)
                        continue
                    paths, check = self.extract_(os_slide, slide_name, label, paths, x_, y_,
                                                 class_size_to_patch_path, is_TMA=self.is_TMA)
                    if check:
                        num_extracted += 1
                        extracted_coordinates[label].append((x_, y_))
                        coords.add_coord(label, x_, y_)
        utils.save_hdf5(hd5_file_path, paths, self.patch_size)
        if self.store_thumbnail:
            mask = self.mask[slide_name] if self.use_mask and slide_name in self.mask else None
            PlotThumbnail(slide_name, os_slide, hd5_file_path, self.slide_annotation[slide_name], mask=mask)
        send_end.send(coords)

    def extract_patch_by_entire_slide(self, slide_path,
            class_size_to_patch_path, send_end):
        """Extracts patches using the steps:
         1. Moves a sliding, non-overlaping window to extract each patch to Pillow patch.
         2. Converts patch to ndarray ndpatch and skips to next patch if background

        Parameters
        ----------
        slide_path : str
            Path of slide to extract patch

        class_size_to_patch_path : dict
            To get the patch path a store evaluated patch using evaluated label name and patch size as keys

        send_end : multiprocessing.connection.Connection
            Connection to send recorded coords metadata of a slide to parent.
        """
        slide_name = utils.path_to_filename(slide_path)
        os_slide = OpenSlide(slide_path)
        coords = CoordsMetadata(slide_name, patch_size=self.patch_size)
        num_extracted = 0
        extracted_coordinates = defaultdict(list)
        paths = []
        label = 'Mix'
        hd5_file_path = os.path.join(self.hd5_location, f"{slide_name}.h5")
        shuffle_coordinate = True if self.max_slide_patches is not None else False
        for data in SlideCoordsExtractor(os_slide, self.patch_size, patch_overlap=0.0,
                                         shuffle=shuffle_coordinate, seed=self.seed,
                                         is_TMA=False, stride=self.stride):
            if self.max_slide_patches is not None and num_extracted >= self.max_slide_patches:
                """Stop extracting patches once we have reach the max number of them for this slide.
                """
                break
            tile_x, tile_y, x, y = data
            if self.use_mask and slide_name in self.mask:
                check_tissue = self.check_tissue(slide_name, x, y)
                if not check_tissue:
                    continue
            if self.use_radius:
                # stride = int((1-self.patch_overlap)*self.patch_size)
                stride = self.patch_size
                Coords = utils.get_circular_coordinates(self.radius, x, y, stride,
                                            os_slide.dimensions, self.patch_size)
            else:
                Coords = [(x, y)]
            # check main image; if it is background, skip it
            check = self.extract_(os_slide, slide_name, label, paths, x, y, class_size_to_patch_path,
                                  check_background=True)
            if not check:
                continue
            for coord in Coords:
                x_, y_ = coord
                if self.use_mask and slide_name in self.mask:
                    check_tissue = self.check_tissue(slide_name, x_, y_)
                    if not check_tissue:
                        continue
                if (x_, y_) in extracted_coordinates[label]: # it has been previously extracted (usefull for radius)
                    continue
                paths, check = self.extract_(os_slide, slide_name, label, paths, x_, y_,
                                             class_size_to_patch_path)
                if check:
                    num_extracted += 1
                    extracted_coordinates[label].append((x_, y_))
                    coords.add_coord(label, x_, y_)
        utils.save_hdf5(hd5_file_path, paths, self.patch_size)
        if self.store_thumbnail:
            mask = self.mask[slide_name] if self.use_mask and slide_name in self.mask else None
            PlotThumbnail(slide_name, os_slide, hd5_file_path, None, mask=mask)
        send_end.send(coords)

    def extract_patch_by_mosaic(self, slide_path,
            class_size_to_patch_path, send_end):
        """Extracts patches using the steps:
         1. Moves a sliding, non-overlaping window to extract each patch to Pillow patch.
         2. Converts patch to ndarray ndpatch and skips to next patch if background

        Parameters
        ----------
        slide_path : str
            Path of slide to extract patch

        class_size_to_patch_path : dict
            To get the patch path a store evaluated patch using evaluated label name and patch size as keys

        send_end : multiprocessing.connection.Connection
            Connection to send recorded coords metadata of a slide to parent.
        """
        slide_name = utils.path_to_filename(slide_path)
        os_slide = OpenSlide(slide_path)
        coords = CoordsMetadata(slide_name, patch_size=self.patch_size)
        dict_hist_coord = {'hist': [], 'coords': []}
        dict_num_patch = {'total': 0, 'tissue': 0, 'selected': 0, 'radius': 0}
        label = "Mosaic"
        extracted_coordinates = defaultdict(list)
        hd5_file_path = os.path.join(self.hd5_location, f"{slide_name}.h5")
        for data in SlideCoordsExtractor(os_slide, self.patch_size, patch_overlap=0.0,
                                         shuffle=False, seed=self.seed,
                                         is_TMA=False, stride=self.stride):

            tile_x, tile_y, x, y = data
            if self.use_mask and slide_name in self.mask:
                check_tissue = self.check_tissue(slide_name, x, y)
                if not check_tissue:
                    continue
            dict_num_patch['total'] += 1
            patch = preprocess.extract(os_slide, x, y, self.patch_size)
            ndpatch = utils.image.preprocess.pillow_image_to_ndarray(patch)
            check = utils.image.preprocess.check_luminance(ndpatch)
            if check:
                dict_num_patch['tissue'] += 1
                eval_patch = preprocess.resize(patch, self.evaluation_size)
                # Get the color histogram of the image
                hist = np.array(eval_patch.histogram())
                dict_hist_coord['hist'].append(hist)
                dict_hist_coord['coords'].append(np.array([x, y]))
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=0)
        if self.n_clusters > len(dict_hist_coord['hist']):
            logger.info(f"No patches can be selected from {slide_name}.")
            send_end.send(None)
            return
        clusters = kmeans.fit_predict(dict_hist_coord['hist'])
        # Another Kmeans on location
        paths = []
        for n_cluster in range(self.n_clusters):
            idx = np.where(clusters==n_cluster)[0]
            if len(idx)==0: continue
            selected_coords = np.array(dict_hist_coord['coords'])[idx]
            n_clusters = math.ceil(len(idx) * self.percentage)
            if n_clusters > len(idx): continue
            kmeans_ = KMeans(n_clusters=n_clusters, random_state=0)
            kmeans_.fit(selected_coords)
            # Find the nearest
            final_idx = np.argmin(kmeans_.transform(selected_coords), axis=0)
            for idx_ in final_idx:
                dict_num_patch['selected'] += 1
                x, y = selected_coords[idx_]
                if self.use_radius:
                    stride = self.patch_size
                    Coords = utils.get_circular_coordinates(self.radius, x, y, stride,
                                                os_slide.dimensions, self.patch_size)
                else:
                    Coords = [(x, y)]
                for coord in Coords:
                    x_, y_ = coord
                    if self.use_mask and slide_name in self.mask:
                        check_tissue = self.check_tissue(slide_name, x_, y_)
                        if not check_tissue:
                            continue
                    if (x_, y_) in extracted_coordinates[label]: # it has been previously extracted (usefull for radius)
                        continue
                    paths, check = self.extract_(os_slide, label, paths, x_, y_,
                                                 class_size_to_patch_path)
                    if check:
                        dict_num_patch['radius'] += 1
                        extracted_coordinates[label].append((x_, y_))
                        coords.add_coord(label, x_, y_)
        print(f"From {dict_num_patch['total']} total patches, {dict_num_patch['tissue']} "
              f" of them contains tissue, and {dict_num_patch['selected']} are selected"
              f" for representing {slide_name}.")
        if self.use_radius:
            print(f"In total, {dict_num_patch['radius']} are extracted because of "
                  "using radius option!")
        utils.save_hdf5(hd5_file_path, paths, self.patch_size)
        if self.store_thumbnail:
            mask = self.mask[slide_name] if self.use_mask and slide_name in self.mask else None
            PlotThumbnail(slide_name, os_slide, hd5_file_path, None, mask=mask)
        send_end.send(coords)

    def produce_args(self, cur_slide_paths):
        """Produce arguments to send to patch extraction subprocess. Creates subdirectories for patches if necessary.

        Parameters
        ----------
        cur_slide_paths : list of str
            List of slide paths. Each path is sent to a subprocess to get slide to extract.

        Returns
        -------
        list of tuple
            List of argument tuples to pass through each process. Each argument tuple contains:
             - slide_path (str) path of slide to extract patch.
             - class_size_to_patch_path (dict of str: dict) to get the patch path a store resized patch using annotated label name and patch size as keys
        """
        args = []
        for slide_path in cur_slide_paths:
            slide_name = utils.path_to_filename(slide_path)
            if self.should_use_manifest:
                if 'subtype' in self.manifest:
                    idx = self.manifest['slide_path'].index(slide_path)
                    subtype_ = self.manifest['subtype'][idx]
                    slide_id = f"{subtype_}/{slide_name}"
                else:
                    slide_id = slide_name
            else:
                slide_id = utils.create_patch_id(slide_path, self.slide_pattern)
            def make_patch_path(class_name):
                """Create patch path and cache it by size in resize_sizes using slide_id from method body.
                """
                size_patch_path = { }
                for resize_size in self.resize_sizes:
                    size_patch_path[resize_size] = os.path.join(
                            self.patch_location, class_name, slide_id,
                            str(resize_size), str(self.get_magnification(resize_size)))
                    if self.store_extracted_patches or self.should_use_hd5_files:
                        os.makedirs(size_patch_path[resize_size], exist_ok=True)
                return size_patch_path

            class_size_to_patch_path = { }
            if self.should_use_annotation:
                if slide_name not in self.slide_annotation:
                    """Skip slide as there are no annotations for it.
                    """
                    continue
                if self.is_tumor:
                    tumor_label = BinaryEnum(1).name
                    if tumor_label in self.slide_annotation[slide_name].labels:
                        class_size_to_patch_path[tumor_label] = make_patch_path(tumor_label)
                else:
                    for label in self.slide_annotation[slide_name].labels:
                        class_size_to_patch_path[label] = make_patch_path(label)
            elif self.should_use_entire_slide:
                label = "Mix"
                class_size_to_patch_path[label] = make_patch_path(label)
            elif self.should_use_mosaic:
                label = "Mosaic"
                class_size_to_patch_path[label] = make_patch_path(label)
            elif self.should_use_slide_coords:
                if not self.slide_coords_metadata.has_slide(slide_name):
                    """Skip slide as there are no slide coordinates for it.
                    """
                    continue
                if self.is_tumor:
                    tumor_label = BinaryEnum(1).name
                    if tumor_label in self.slide_coords_metadata \
                            .get_slide(slide_name).labels:
                        class_size_to_patch_path[tumor_label] \
                                = make_patch_path(tumor_label)
                else:
                    for label in self.slide_coords_metadata \
                            .get_slide(slide_name).labels:
                        class_size_to_patch_path[label] = make_patch_path(label)
            elif self.should_use_hd5_files:
                pass
            else:
                raise NotImplementedError(f"Extract method {self.extract_method} not implemented")
            arg = (slide_path, class_size_to_patch_path)
            args.append(arg)
        return args

    def run(self):
        """Run extract annotated patches.
        """
        self.print_parameters()
        if self.n_process > self.MAX_N_PROCESS:
            logger.info(f"Number of CPU processes of {self.n_process} is too high. Setting to {self.MAX_N_PROCESS}")
            self.n_process = self.MAX_N_PROCESS
        logger.info(f"Number of CPU processes: {self.n_process}")
        if hasattr(self, 'slide_idx') and self.slide_idx is not None:
            self.slide_paths = utils.select_slides(self.slide_paths, self.slide_idx, self.n_process)
        n_slides = len(self.slide_paths)
        if n_slides==1:
            logger.info(f"Extracting patches from {self.slide_paths}")
        coords_to_merge = []
        prefix = "Extracting from slides: "
        for idx in tqdm(range(0, n_slides, self.n_process),
                desc=prefix, dynamic_ncols=True):
            cur_slide_paths = self.slide_paths[idx:idx + self.n_process]
            processes = []
            recv_end_list = []
            for args in self.produce_args(cur_slide_paths):
                if self.should_use_hd5_files:
                    p = mp.Process(target=self.extract_patch_by_hd5_files, args=args)
                elif self.should_use_annotation:
                    recv_end, send_end = mp.Pipe(False)
                    recv_end_list.append(recv_end)
                    args = (*args, send_end,)
                    p = mp.Process(target=self.extract_patch_by_annotation, args=args)
                elif self.should_use_entire_slide:
                    recv_end, send_end = mp.Pipe(False)
                    recv_end_list.append(recv_end)
                    args = (*args, send_end,)
                    p = mp.Process(target=self.extract_patch_by_entire_slide, args=args)
                elif self.should_use_mosaic:
                    recv_end, send_end = mp.Pipe(False)
                    recv_end_list.append(recv_end)
                    args = (*args, send_end,)
                    p = mp.Process(target=self.extract_patch_by_mosaic, args=args)
                elif self.should_use_slide_coords:
                    p = mp.Process(target=self.extract_patch_by_slide_coords, args=args)
                p.start()
                processes.append(p)
            coords_to_merge.extend(map(lambda x: x.recv(), recv_end_list))
            for p in processes:
                p.join()

        if self.should_use_annotation:
            """Merge slide coords
            """
            logger.info("Done loop. Saving slide coordinate metadata.")
            slide_coords = SlideCoordsMetadata(self.slide_coords_location,
                    patch_size=self.patch_size, resize_sizes=self.__resize_sizes)
            slide_coords.consume_coords(coords_to_merge)
            slide_coords.save()
        logger.info("Done.")
