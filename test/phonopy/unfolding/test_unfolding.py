from __future__ import print_function
import unittest
import sys
import numpy as np
from phonopy.structure.cells import get_supercell
from phonopy.unfolding import Unfolding
from phonopy import Phonopy
from phonopy.interface.vasp import read_vasp
from phonopy.file_IO import parse_FORCE_SETS, parse_BORN
from phonopy.structure.atoms import PhonopyAtoms
# from phonopy.structure.atoms import Atoms
# from phonopy.interface.vasp import write_vasp

class TestUnfolding(unittest.TestCase):

    def setUp(self):
        self._cell = read_vasp("POSCAR")
        # print(PhonopyAtoms(atoms=self._cell))
        self._unfolding = None
    
    def tearDown(self):
        pass
    
    def test_Unfolding_NaCl(self):
        ## mesh
        # nd = 10
        # qpoints = np.array(list(np.ndindex(nd, nd, nd))) / float(nd)
        ## band
        nd = 100
        qpoints = np.array([[x,] * 3 for x in range(nd)]) / float(nd)

        unfolding_supercell_matrix=[[-2, 2, 2],
                                    [2, -2, 2],
                                    [2, 2, -2]]
        self._prepare_unfolding(qpoints, unfolding_supercell_matrix)
        self._run_unfolding()
        weights = self._get_weights(qpoints, unfolding_supercell_matrix)
        # self._write_weights(weights, "unfolding.dat")
        self._compare(weights, "unfolding.dat")

    def test_Unfolding_SC(self):
        ## mesh
        # nd = 10
        # qpoints = np.array(list(np.ndindex(nd, nd, nd))) / float(nd)
        ## band
        nd = 100
        qpoints = np.array([[x,] * 3 for x in range(nd)]) / float(nd)

        unfolding_supercell_matrix = np.diag([4, 4, 4])
        self._prepare_unfolding(qpoints, unfolding_supercell_matrix)
        self._run_unfolding()
        weights = self._get_weights(qpoints, unfolding_supercell_matrix)
        # self._write_weights(weights, "unfolding_to_atoms.dat")
        self._compare(weights, "unfolding_to_atoms.dat")

    def _compare(self, weights, filename):
        with open(filename) as f:
            weights_in_file = np.loadtxt(f)
            self.assertTrue((np.abs(weights_in_file - weights) < 1e-3).all())

    def _prepare_unfolding(self, qpoints, unfolding_supercell_matrix):
        supercell = get_supercell(self._cell, np.diag([2, 2, 2]))
        phonon = self._get_phonon(supercell)
        self._set_nac_params(phonon)
        mapping = range(supercell.get_number_of_atoms())
        self._unfolding = Unfolding(phonon,
                                    unfolding_supercell_matrix,
                                    supercell.get_scaled_positions(),  
                                    mapping,
                                    qpoints)

    def _run_unfolding(self):
        self._unfolding.run(verbose=False)
        # print(self._unfolding.get_unfolding_weights().shape)

    def _get_weights(self, qpoints, unfolding_supercell_matrix):
        P = np.linalg.inv(unfolding_supercell_matrix)
        comm_points = self._unfolding.get_commensurate_points()
        # (nd + 1, num_atom_super / num_atom_prim, num_atom_super * 3)
        weights = self._unfolding.get_unfolding_weights() 
        freqs = self._unfolding.get_frequencies()

        out_vals = []
        for i, q in enumerate(qpoints):
            q_prim = np.dot(P.T, q)
            for j, G in enumerate(comm_points):
                q_k = q_prim + G
                q_k -= np.rint(q_k)
                if (np.abs(q_k[0] - q_k[1:]) > 1e-5).any():
                    continue
                for k, f in enumerate(freqs[i]):
                    uw = weights[i, k, j]
                    out_vals.append([q_k[0], q_k[1], q_k[2], f, uw])

        return out_vals

    def _write_weights(self, weights, filename):
        with open(filename, 'w') as w:
            lines = ["%10.7f %10.7f %10.7f  %12.7f  %10.7f" % tuple(x)
                     for x in weights]
            w.write("\n".join(lines))

    def _get_phonon(self, cell):
        phonon = Phonopy(cell,
                         np.diag([1, 1, 1]),
                         is_auto_displacements=False)
        force_sets = parse_FORCE_SETS()
        phonon.set_displacement_dataset(force_sets)
        phonon.produce_force_constants()
        return phonon

    def _set_nac_params(self, phonon):
        supercell = phonon.get_supercell()
        born_elems = {'Na': [[1.08703, 0, 0],
                             [0, 1.08703, 0],
                             [0, 0, 1.08703]],
                      'Cl': [[-1.08672, 0, 0],
                             [0, -1.08672, 0],
                             [0, 0, -1.08672]]}
        born = [born_elems[s]
                for s in supercell.get_chemical_symbols()]
        epsilon = [[2.43533967, 0, 0],
                   [0, 2.43533967, 0],
                   [0, 0, 2.43533967]]
        factors = 14.400
        phonon.set_nac_params({'born': born,
                               'factor': factors,
                               'dielectric': epsilon})

if __name__ == '__main__':
    unittest.main()
