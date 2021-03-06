"""
Ncpol2SDPA
=====

Provides
 1. A converter from a polynomial optimization problems of commuting and
    noncommuting variables to a semidefinite programming relaxation.
 2. Helper functions to define physics problems.

"""

__all__ = ['SdpRelaxation',
           'generate_variables',
           'get_ncmonomials',
           'ncdegree',
           'save_monomial_index',
           'bosonic_constraints',
           'fermionic_constraints',
           'projective_measurement_constraints',
           'correlator',
           'maximum_violation',
           'generate_measurements',
           'define_objective_with_I',
           'flatten',
           'get_neighbors',
           'solve_sdp',
           'get_xmat_value',
           'write_to_sdpa',
           'find_rank_loop',
           'read_sdpa_out',
           'pauli_constraints',
           'convert_to_mosek',
           'convert_to_picos',
           'convert_to_picos_extra_moment_matrix',
           'write_to_human_readable',
           'sos_decomposition']

from .sdp_relaxation import SdpRelaxation
from .nc_utils import generate_variables, get_ncmonomials, ncdegree, flatten, \
                      save_monomial_index
from .sdpa_utils import write_to_sdpa, read_sdpa_out, write_to_human_readable
from .solver_common import solve_sdp, find_rank_loop, sos_decomposition, \
                           get_xmat_value
from .physics_utils import bosonic_constraints, fermionic_constraints, \
    pauli_constraints, get_neighbors, correlator, generate_measurements, \
    projective_measurement_constraints, \
    maximum_violation, define_objective_with_I
from .mosek_utils import convert_to_mosek
from .picos_utils import convert_to_picos, \
    convert_to_picos_extra_moment_matrix
