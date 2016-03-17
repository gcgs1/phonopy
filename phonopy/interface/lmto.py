# LMTO INTERFACE TO PHONOPY
# -------------------------
# --- LMTO CLASS: Parses an lmto site file. Need to rewrite some
#                 sections. LMTO can now read site files generated by 
#                 phonopy. Class implementation improved.
#     LAST EDITED: 16.00 17/03/2016
#     VERSION: 0.6 --- gcgs

from __future__ import print_function
from phonopy.file_IO import get_drift_forces
from phonopy.interface.vasp import sort_positions_by_symbols
#from phonopy.interface.vasp import get_scaled_positions_lines
>>>>>>> lmto_interface
from phonopy.units import Bohr
from phonopy.structure.atoms import Atoms, symbol_map

import sys
import numpy as np

def parse_set_of_forces(num_atoms, forces_filenames):
    force_sets = []
    for filename in forces_filenames:
        lmto_forces = []
        with open(filename, 'r') as f:
            for line in f:
                if line.strip().startswith('%'): continue
                else:
                    lmto_forces.append(
                        [float(line.split()[i]) for i in xrange(3)])
                if len(lmto_forces) == num_atoms: break
    
        if not lmto_forces:
            return []

        drift_force = get_drift_forces(lmto_forces)
        force_sets.append(np.array(lmto_forces) - drift_force)

    return force_sets

def read_lmto(filename):
    with open(filename, 'r') as f: lines = f.readlines()
    
    header = lines[0]
    sites = lines[2:]
    
    lmto_in = LMTOIn(header, sites)
    tags = lmto_in.get_variables(header, sites)

    plat = [tags['alat'] * np.array(tags['plat'][i]) for i in xrange(3)]
    positions = tags['atoms']['positions']
    symbols = tags['atoms']['spfnames']
    
    spfnames = list(set(symbols))    
    numbers = []
    for s in symbols:
        numbers.append(symbol_map[s])

    return Atoms(numbers=numbers,
                 cell=plat,
                 scaled_positions=positions)

def write_lmto(filename, cell):
    with open(filename, 'w') as f: f.write(get_lmto_structure(cell))

def write_supercells_with_displacements(supercell,
                                        cells_with_displacements, ext):
    write_lmto('supercell.' + ext, supercell)
    for i, cell in enumerate(cells_with_displacements):
        write_lmto('supercell-%03d.' % (i + 1) + ext, cell)

def get_lmto_structure(cell):
    lattice = cell.get_cell()
    (num_atoms,
     symbols,
     scaled_positions,
     sort_list) = sort_positions_by_symbols(cell.get_chemical_symbols(),
                                            cell.get_scaled_positions())
    
    lines = '% site-data vn=3.0 xpos fast io=62'
    lines += ' nbas=%d' % sum(num_atoms)
    lines += ' alat=1.0'
    lines += ' plat=' + (' %10.7f' * 9 + '\n') % tuple(lattice.ravel())
    lines += '#' + '                        ' + 'pos'
    lines += '                                   ' + 'vel'
    lines += '                                    ' + 'eula'
    lines += '                   ' + 'vshft  PL rlx\n'
    count = 0
    for n in xrange(len(num_atoms)):
        i = 0
        while i < num_atoms[n]:
            lines += ' ' + symbols[n]
            for x in xrange(3): 
                lines += 3*' ' + '%10.7f' % scaled_positions[count, x]
            for y in xrange(7):
                lines += 3*' ' + '%10.7f' % 0
            lines += ' 0 111'
            lines += '\n'
            i += 1; count += 1

    return lines

class LMTOIn:
    def __init__(self, header, sites):
        self._set_methods = {'atoms': self._set_atoms,
                             'plat':  self._set_plat,
                             'alat':  self._set_alat}
        self._tags = {'atoms': None,
                      'plat':  None,
                      'alat':  1.0}

    def _set_atoms(self, sites):
        spfnames = []
        positions = []
        for i in sites:
            spfnames.append(i.split()[0])
            positions.append([float(x) for x in i.split()[1:4]])
        self._tags['atoms'] = {'spfnames':  spfnames,
                               'positions': positions}

    def _set_plat(self, header):
        plat = []
        hlist = header.split()
        index = hlist.index('plat=')
        for j in xrange(1, 10, 3):
            plat.append([float(x) for x in hlist[index+j:index+j+3]])
        self._tags['plat'] = plat

    def _set_alat(self, header):
        hlist = header.split()
        for j in hlist:
            if j.startswith('alat'):
                alat = float(j.split('=')[1])
                break
        self._tags['alat'] = alat    

    def _check_ord(self, header):
        if not 'xpos' in header.split():
            print('EXIT(1): LMTO Interface requires site', end=' ')
            print('files to be in fractional co-ordinates')
            sys.exit(1)
            
    def get_variables(self, header, sites):
        self._check_ord(header)
        self._set_atoms(sites)
        self._set_plat(header)
        self._set_alat(header)
        return self._tags

if __name__ == '__main__':
    import sys
    from phonopy.structure.symmetry import Symmetry
    cell = read_lmto(sys.argv[1])
    symmetry = Symmetry(cell)
    print('# %s' % symmetry.get_international_table())
    print(get_lmto_structure(cell))
