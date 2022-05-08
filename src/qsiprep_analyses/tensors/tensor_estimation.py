"""
Definition of the :class:`TensorEstimation` class.
"""
import warnings
from pathlib import Path
from typing import List, Tuple, Union

import tqdm
from analyses_utils.entities.derivatives.qsiprep import QsiprepDerivatives
from dipy.workflows.reconst import ReconstDkiFlow, ReconstDtiFlow

from qsiprep_analyses.data.bids import build_relative_path
from qsiprep_analyses.qsiprep_analysis import QsiprepAnalysis
from qsiprep_analyses.tensors.messages import (
    INVALID_OUTPUT,
    INVALID_PARTICIPANT,
    TENSOR_RECONSTRUCTION_NOT_IMPLEMENTED,
)
from qsiprep_analyses.tensors.utils.templates import (
    KWARGS_MAPPING,
    TENSOR_DERIVED_ENTITIES,
    TENSOR_DERIVED_METRICS,
)


class TensorEstimation(QsiprepAnalysis):
    #: Templates
    TENSOR_ENTITIES = TENSOR_DERIVED_ENTITIES.copy()
    METRICS = TENSOR_DERIVED_METRICS.copy()

    #: Tensor Workflows
    TENSOR_FITTING_KWARGS = KWARGS_MAPPING
    TENSOR_WORKFLOWS = {
        "diffusion_tensor": ReconstDtiFlow,
        "diffusion_kurtosis": ReconstDkiFlow,
        "restore_tensor": ReconstDtiFlow,
    }
    #: Tensor types
    TENSOR_TYPES = dict(
        diffusion_tensor={"acq": "dt", "fit_method": "WLS"},
        diffusion_kurtosis={"acq": "dk", "fit_method": "WLS"},
        restore_tensor={"acq": "rt", "fit_method": "restore"},
    )

    def __init__(
        self,
        derivatives: QsiprepDerivatives = None,
        base_dir: Union[Path, str] = None,
        participant_label: str = None,
        sessions_base: str = None,
    ):
        super().__init__(
            derivatives, base_dir, participant_label, sessions_base
        )

    def validate_tensor_type(self, tensor_type: str) -> None:
        """
        Validates *tensor_type* as an implemented tensor estimation protocol.

        Parameters
        ----------
        tensor_type : str
            The tensor estimation method (either "dt" or "dk")

        Raises
        ------
        NotImplementedError
            In case *tensor_type* is not an implemented key of recognized
            tensor-estimation protocol
        """
        if tensor_type not in self.TENSOR_TYPES:
            raise NotImplementedError(
                TENSOR_RECONSTRUCTION_NOT_IMPLEMENTED.format(
                    tensor_type=tensor_type
                )
            )
        return self.TENSOR_TYPES.get(tensor_type)

    def validate_requested_output(self, tensor_type: str, output: str) -> bool:
        """
        Validates a requested output to be a valid *tensor_type* derived metric

        Parameters
        ----------
        tensor_type : str
            The tensor estimation method (either "dt" or "dk")
        output : str
            The requested output

        Returns
        -------
        bool
            Whether the requested *output* is a valid output of *tensor_type*
            derived metrics
        """
        if output in self.METRICS.get(tensor_type):
            return True
        else:

            warnings.warn(
                INVALID_OUTPUT.format(
                    output=output,
                    tensor_type=tensor_type,
                    available_metrics=", ".join(self.METRICS.get(tensor_type)),
                )
            )
            return False

    def build_output_dictionary(
        self, source: Path, tensor_type: str, outputs: List[str] = None
    ) -> dict:
        """
        Based on a *source* DWI, reconstruct output names for tensor-derived
        metric available under *tensor_type*.

        Parameters
        ----------
        source : Path
            The source DWI file.
        tensor_type : str
            The tensor estimation method (either "dt" or "dk")
        outputs : list, optional
            Requested tensor-derived outputs, by default All available

        Returns
        -------
        dict
            A dictionary with keys of available/requested outputs and their
            corresponding paths
        """
        outputs = outputs or self.METRICS.get(tensor_type)
        target = {}
        for output in outputs:
            if self.validate_requested_output(tensor_type, output):
                output_parts = output.split("_")
                if len(output_parts) > 1:
                    output_desc = "".join(
                        [output_parts[0], output_parts[1].capitalize()]
                    )
                else:
                    output_desc = output
                target[
                    f"out_{output}"
                ] = self.derivatives.path.parent / build_relative_path(
                    source,
                    {
                        "acquisition": self.TENSOR_TYPES.get(tensor_type).get(
                            "acq"
                        ),
                        "desc": output_desc,
                        **self.TENSOR_ENTITIES,
                    },
                )

        return target
