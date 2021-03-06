# procar.py: Parses PROCAR file
#
# Copyright (c) 2013 Tim Lovorn (tflovorn@crimson.ua.edu)
# Released under the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#     The above copyright notice and this permission notice shall be included in
#     all copies or substantial portions of the Software.
#
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#     IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#     FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#     AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#     LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#     OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#     THE SOFTWARE.
#
import re

# Represents the data stored in a PROCAR file.
# Contains properties nonCol, Nk, Nb, Ni, and kPoints.
# kPoints is a list of KPoint objects.
class PROCAR(object):
    # Create PROCAR object by reading from the file-like object procarFile.
    # nonCol = true if this is a non-collinear calculation (2 spins: 4 spinor
    # components); otherwise nonCol = false.
    # If lmDecomposed=False, all ion table columns are discared except the
    # total column. If storeIds=False, entry ids are not stored.
    def __init__(self, procarFile, nonCol, lmDecomposed=True, storeIds=True):
        self.nonCol = nonCol
        self.lmDecomposed = lmDecomposed
        self.storeIds = storeIds

        # Start at the beginning of the file
        try:
            procarFile.seek(0)
        except:
            # if we can't seek, assume we are at the beginning
            print("warning: Couldn't seek to start of PROCAR file")

        # Get global data
        procarFile.readline()                # discard line 1
        globalLine = procarFile.readline()   # globals are on line 2
        # (number of k-points, bands, and ions)
        self.Nk, self.Nb, self.Ni = map(int, re.findall(r'\d+', globalLine))
        procarFile.readline()       # discard line 3 (empty)
        # Iterate over k-points.
        # The next line read should be the first line of the first k-point entry.
        self.kPoints = []
        for kId in range(1, self.Nk+1):
            # Extract k-point data.
            self.kPoints.append(KPoint(procarFile, self, kId))
            # Advance to the next k-point.
            procarFile.readline() # empty line

    # Return data for the k-point with id given by kId in the PROCAR file
    # format (the first id is 1, not 0).
    def KPoint(self, kId):
        return self.kPoints[kId-1]
   
# Represents the data for one k-point.
# Contains properties kId, kx, ky, kz, weight, and bands.
# bands is a list of Band objects.
class KPoint(object):
    # Extract k-point data from procarFile.
    # The next line read should be the first line of the k-point entry.
    def __init__(self, procarFile, procar, kId):
        if procar.storeIds:
            self.kId = kId
        kHead = procarFile.readline()
        # fixed positions since numbers overlap when there is a minus sign
        self.kx, self.ky, self.kz = map(float, [kHead[18:29], kHead[29:40],
                                                kHead[40:51]])
        # weight is the last thing in the line, isolated by spaces
        self.weight = float(kHead.rstrip().split(' ')[-1])
        procarFile.readline() # empty line
        # iterate over bands
        self.bands = []
        for bandId in range(1, procar.Nb+1):
            # Extract band data.
            self.bands.append(Band(procarFile, procar, bandId))
            # Advance to the next band.
            procarFile.readline() # empty line

    # Return data for the band with id given by bandId in the PROCAR file
    # format (the first id is 1, not 0).
    def Band(self, bandId):
        return self.bands[bandId-1]


# Represents the data for one band belonging to a specific k-point.
# Contains properties bandId, energy, occ, tables.
# tables is a list of IonTable objects.
class Band(object):
    # Extract band data from procarFile.
    # The next line read should be the first line of the band entry.
    def __init__(self, procarFile, procar, bandId):
        if procar.storeIds:
            self.bandId = bandId
        bandHead = procarFile.readline().strip().split()
        # energy is the fifth group in the line, isolated by spaces
        self.energy = float(bandHead[4])
        # occ is the last group in the line, isolated by spaces
        self.occ = float(bandHead[-1])
        # get ion tables
        procarFile.readline() # empty line
        procarFile.readline()  # skip line containing "ion   s   py  pz"...etc
        self.tables = []
        numTables = 1
        if procar.nonCol:
            numTables = 4
        for tableId in range(1, numTables+1):
            # Extract table data.
            self.tables.append(IonTable(procarFile, procar, tableId))
        # top/bottom surface weights
        self.top = []
        self.bottom = []

    # Return data for the table with id given by tableId in the PROCAR file
    # format (the first id is 1, not 0).
    def Table(self, tableId):
        return self.tables[tableId-1]


# Represents a table of ionic data belonging to a (k-point, band) pair.
# Contains properties tableId, ions, tot.
# ions is a list of Ion objects and tot is an Ion object containing the
# total values summed over all ions.
class IonTable(object):
    # Extract ion table data from procarFile.
    # The next line read should be the first line of the table, containing ion 1
    def __init__(self, procarFile, procar, tableId):
        if procar.storeIds:
            self.tableId = tableId
        # read data for each ion
        self.ions = []
        for ionId in range(1, procar.Ni+1):
            if procar.lmDecomposed:
                self.ions.append(Ion(procarFile, procar, ionId))
            else:
                self.ions.append(IonTotalOnly(procarFile, procar, ionId))
        # read row containing totals
        if procar.lmDecomposed:
            self.tot = Ion(procarFile, procar, 0)
        else:
            self.tot = IonTotalOnly(procarFile, procar, 0)

    # Return data for the ion with id given by ionId in the PROCAR file
    # format (the first id is 1, not 0).
    def Ion(self, ionId):
        return self.ions[ionId-1]

# Represents data for one ion, belonging to a (k-point, band, ionTable).
# Contains properties ionId, s, py, pz, px, dxy, dyz, dz2, dxz, dx2, tot.
class Ion(object):
    def __init__(self, procarFile, procar, ionId):
        if procar.storeIds:
            self.ionId = ionId
        # each entry in the line is always separated by spaces
        l = procarFile.readline().strip().split()
        self.s, self.py, self.pz, self.px = map(float, [l[1], l[2], l[3], l[4]])
        self.dxy, self.dyz, self.dz2, self.dxz = map(float, [l[5], l[6], l[7], l[8]])
        self.dx2, self.tot = map(float, [l[9], l[10]])

    def SquareSum(self):
        return sum(map(lambda x: x*x, [self.s, self.py, self.pz, self.px,
                                   self.dxy, self.dyz, self.dz2, self.dxz,
                                   self.dx2]))

# Represents data for one ion, belonging to a (k-point, band, ionTable).
# Discards lm-decomposed data. Contains properties ionId, tot.
class IonTotalOnly(object):
    def __init__(self, procarFile, procar, ionId):
        if procar.storeIds:
            self.ionId = ionId
        # each entry in the line is always separated by spaces
        l = procarFile.readline().strip().split()
        self.tot = float(l[10])

    def SquareSum(self):
        return self.tot*self.tot

if __name__ == "__main__":
    # test - TODO arguments?
    with open('PROCAR', 'r') as procarFile:
        procar = PROCAR(procarFile, nonCol=True, lmDecomposed=False, storeIds=False)
        print(procar.Nk, procar.Nb, procar.Ni)
        print(procar.KPoint(1).Band(1).Table(1).Ion(20).tot)
        raw_input("-->")
