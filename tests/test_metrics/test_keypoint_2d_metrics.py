# Copyright (c) OpenMMLab. All rights reserved.
from unittest import TestCase

import numpy as np
import torch
from mmengine.data import InstanceData

from mmpose.datasets.datasets2.utils import parse_pose_metainfo
from mmpose.metrics import AUC, EPE, NME, PCKAccuracy


class TestPCKAccuracy(TestCase):

    def setUp(self):
        """Setup some variables which are used in every test method.

        TestCase calls functions in this order: setUp() -> testMethod() ->
        tearDown() -> cleanUp()
        """
        self.batch_size = 8
        num_keypoints = 15
        self.data_batch = []
        self.predictions = []

        for i in range(self.batch_size):
            gt_instances = InstanceData()
            keypoints = np.zeros((1, num_keypoints, 2))
            keypoints[0, i] = [0.5 * i, 0.5 * i]
            gt_instances.keypoints = keypoints
            gt_instances.keypoints_visible = np.ones(
                (1, num_keypoints, 1)).astype(bool)
            gt_instances.keypoints_visible[0, (2 * i) % 8, 0] = False
            gt_instances.bboxes = np.random.random((1, 4)) * 20 * i
            gt_instances.head_size = np.random.random((1, 1)) * 10 * i

            self.data_batch.append(
                {'data_sample': dict(gt_instances=gt_instances.to_dict())})

            pred_instances = InstanceData()
            pred_instances.keypoints = torch.from_numpy(keypoints)
            self.predictions.append(
                {'pred_instances': pred_instances.to_dict()})

    def test_init(self):
        """test metric init method."""
        # test invalid normalized_items
        with self.assertRaisesRegex(
                KeyError, "Should be one of 'bbox', 'head', 'torso'"):
            PCKAccuracy(norm_item='invalid')

    def test_evaluate(self):
        """test PCK accuracy evaluation metric."""
        # test normalized by 'bbox'
        pck_metric = PCKAccuracy(thr=0.5, norm_item='bbox')
        pck_metric.process(self.data_batch, self.predictions)
        pck = pck_metric.evaluate(self.batch_size)
        target = {'pck/@thr-0.5': 1.0}
        self.assertDictEqual(pck, target)

        # test normalized by 'head_size'
        pckh_metric = PCKAccuracy(thr=0.3, norm_item='head')
        pckh_metric.process(self.data_batch, self.predictions)
        pckh = pckh_metric.evaluate(self.batch_size)
        target = {'pck/PCKh@thr-0.3': 1.0}
        self.assertDictEqual(pckh, target)

        # test normalized by 'torso_size'
        tpck_metric = PCKAccuracy(thr=0.05, norm_item=['bbox', 'torso'])
        tpck_metric.process(self.data_batch, self.predictions)
        tpck = tpck_metric.evaluate(self.batch_size)
        self.assertIsInstance(tpck, dict)
        target = {
            'pck/@thr-0.05': 1.0,
            'pck/Head@thr-0.05': 1.0,
            'pck/Sho@thr-0.05': 1.0,
            'pck/Elb@thr-0.05': 1.0,
            'pck/Wri@thr-0.05': 1.0,
            'pck/Hip@thr-0.05': 1.0,
            'pck/Knee@thr-0.05': 1.0,
            'pck/Ank@thr-0.05': 1.0,
            'pck/Mean@thr-0.05': 1.0,
        }
        self.assertDictEqual(tpck, target)


class TestAUCandEPE(TestCase):

    def setUp(self):
        """Setup some variables which are used in every test method.

        TestCase calls functions in this order: setUp() -> testMethod() ->
        tearDown() -> cleanUp()
        """
        output = np.zeros((1, 5, 2))
        target = np.zeros((1, 5, 2))
        # first channel
        output[0, 0] = [10, 4]
        target[0, 0] = [10, 0]
        # second channel
        output[0, 1] = [10, 18]
        target[0, 1] = [10, 10]
        # third channel
        output[0, 2] = [0, 0]
        target[0, 2] = [0, -1]
        # fourth channel
        output[0, 3] = [40, 40]
        target[0, 3] = [30, 30]
        # fifth channel
        output[0, 4] = [20, 10]
        target[0, 4] = [0, 10]

        gt_instances = InstanceData()
        gt_instances.keypoints = target
        gt_instances.keypoints_visible = np.array(
            [[True, True, False, True, True]])

        pred_instances = InstanceData()
        pred_instances.keypoints = torch.from_numpy(output)

        self.data_batch = [{
            'data_sample':
            dict(gt_instances=gt_instances.to_dict())
        }]
        self.predictions = [{'pred_instances': pred_instances.to_dict()}]

    def test_auc_evaluate(self):
        """test AUC evaluation metric."""
        auc_metric = AUC(norm_factor=20, num_thrs=4)
        auc_metric.process(self.data_batch, self.predictions)
        auc = auc_metric.evaluate(1)
        target = {'auc/@4thrs': 0.375}
        self.assertDictEqual(auc, target)

    def test_epe_evaluate(self):
        """test EPE evaluation metric."""
        epe_metric = EPE()
        epe_metric.process(self.data_batch, self.predictions)
        epe = epe_metric.evaluate(1)
        self.assertAlmostEqual(epe['epe/epe'], 11.5355339)


class TestNME(TestCase):

    def _generate_data(self,
                       batch_size: int = 1,
                       num_keypoints: int = 5,
                       norm_item: str = 'box_size') -> tuple:
        """Generate data_batch and predictions according to different
        settings."""
        data_batch = []
        predictions = []

        for i in range(batch_size):
            gt_instances = InstanceData()
            keypoints = np.zeros((1, num_keypoints, 2))
            keypoints[0, i] = [0.5 * i, 0.5 * i]
            gt_instances.keypoints = keypoints
            gt_instances.keypoints_visible = np.ones(
                (1, num_keypoints, 1)).astype(bool)
            gt_instances.keypoints_visible[0, (2 * i) % batch_size, 0] = False
            gt_instances[norm_item] = np.random.random((1, 1)) * 20 * i

            data_batch.append(
                {'data_sample': dict(gt_instances=gt_instances.to_dict())})

            pred_instances = InstanceData()
            pred_instances.keypoints = torch.from_numpy(keypoints)
            predictions.append({'pred_instances': pred_instances.to_dict()})

        return data_batch, predictions

    def test_nme_evaluate(self):
        """test NME evaluation metric."""
        # test when norm_mode = 'use_norm_item'
        # test norm_item = 'box_size' like in `AFLWDataset`
        norm_item = 'box_size'
        nme_metric = NME(norm_mode='use_norm_item', norm_item=norm_item)
        aflw_meta_info = dict(from_file='configs/_base_/datasets/aflw.py')
        aflw_dataset_meta = parse_pose_metainfo(aflw_meta_info)
        nme_metric.dataset_meta = aflw_dataset_meta

        data_batch, predictions = self._generate_data(
            batch_size=4, num_keypoints=19, norm_item=norm_item)
        nme_metric.process(data_batch, predictions)
        nme = nme_metric.evaluate(4)
        target = {'nme/@box_size': 0.0}
        self.assertDictEqual(nme, target)

        # test when norm_mode = 'keypoint_distance'
        # when `keypoint_indices = None`,
        # use default `keypoint_indices` like in `Horse10Dataset`
        nme_metric = NME(norm_mode='keypoint_distance')
        horse10_meta_info = dict(
            from_file='configs/_base_/datasets/horse10.py')
        horse10_dataset_meta = parse_pose_metainfo(horse10_meta_info)
        nme_metric.dataset_meta = horse10_dataset_meta

        data_batch, predictions = self._generate_data(
            batch_size=4, num_keypoints=22)
        nme_metric.process(data_batch, predictions)
        nme = nme_metric.evaluate(4)

        target = {'nme/@[0, 1]': 0.0}
        self.assertDictEqual(nme, target)

        # test when norm_mode = 'keypoint_distance'
        # specify custom `keypoint_indices`
        keypoint_indices = [2, 4]
        nme_metric = NME(
            norm_mode='keypoint_distance', keypoint_indices=keypoint_indices)
        coco_meta_info = dict(from_file='configs/_base_/datasets/coco.py')
        coco_dataset_meta = parse_pose_metainfo(coco_meta_info)
        nme_metric.dataset_meta = coco_dataset_meta

        data_batch, predictions = self._generate_data(
            batch_size=2, num_keypoints=17)
        nme_metric.process(data_batch, predictions)
        nme = nme_metric.evaluate(2)

        target = {f'nme/@{keypoint_indices}': 0.0}
        self.assertDictEqual(nme, target)

    def test_exceptions_and_warnings(self):
        """test exceptions and warnings."""
        # test invalid norm_mode
        with self.assertRaisesRegex(
                KeyError,
                "`norm_mode` should be 'use_norm_item' or 'keypoint_distance'"
        ):
            nme_metric = NME(norm_mode='invalid')

        # test when norm_mode = 'use_norm_item' but do not specify norm_item
        with self.assertRaisesRegex(
                KeyError, '`norm_mode` is set to `"use_norm_item"`, '
                'please specify the `norm_item`'):
            nme_metric = NME(norm_mode='use_norm_item', norm_item=None)

        # test when norm_mode = 'use_norm_item'
        # but the `norm_item` do not in data_info
        with self.assertRaisesRegex(
                AssertionError,
                'The ground truth data info do not have the expected '
                'normalized factor'):
            nme_metric = NME(norm_mode='use_norm_item', norm_item='norm_item1')
            coco_meta_info = dict(from_file='configs/_base_/datasets/coco.py')
            coco_dataset_meta = parse_pose_metainfo(coco_meta_info)
            nme_metric.dataset_meta = coco_dataset_meta

            data_batch, predictions = self._generate_data(
                norm_item='norm_item2')
            # raise AssertionError here
            nme_metric.process(data_batch, predictions)

        # test when norm_mode = 'keypoint_distance', `keypoint_indices` = None
        # but the dataset_name not in `DEFAULT_KEYPOINT_INDICES`
        with self.assertRaisesRegex(
                KeyError, 'can not find the keypoint_indices in '
                '`DEFAULT_KEYPOINT_INDICES`'):
            nme_metric = NME(
                norm_mode='keypoint_distance', keypoint_indices=None)
            coco_meta_info = dict(from_file='configs/_base_/datasets/coco.py')
            coco_dataset_meta = parse_pose_metainfo(coco_meta_info)
            nme_metric.dataset_meta = coco_dataset_meta

            data_batch, predictions = self._generate_data()
            nme_metric.process(data_batch, predictions)
            # raise KeyError here
            _ = nme_metric.evaluate(1)

        # test when len(keypoint_indices) is not 2
        with self.assertRaisesRegex(
                AssertionError,
                'The keypoint indices used for normalization should be a pair.'
        ):
            nme_metric = NME(
                norm_mode='keypoint_distance', keypoint_indices=[0, 1, 2])
            coco_meta_info = dict(from_file='configs/_base_/datasets/coco.py')
            coco_dataset_meta = parse_pose_metainfo(coco_meta_info)
            nme_metric.dataset_meta = coco_dataset_meta

            data_batch, predictions = self._generate_data()
            nme_metric.process(data_batch, predictions)
            # raise AssertionError here
            _ = nme_metric.evaluate(1)

        # test when dataset does not contain the required keypoint
        with self.assertRaisesRegex(AssertionError,
                                    'dataset does not contain the required'):
            nme_metric = NME(
                norm_mode='keypoint_distance', keypoint_indices=[17, 18])
            coco_meta_info = dict(from_file='configs/_base_/datasets/coco.py')
            coco_dataset_meta = parse_pose_metainfo(coco_meta_info)
            nme_metric.dataset_meta = coco_dataset_meta

            data_batch, predictions = self._generate_data()
            nme_metric.process(data_batch, predictions)
            # raise AssertionError here
            _ = nme_metric.evaluate(1)