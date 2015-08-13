#!/usr/bin/env python

from openquake.hazardlib.gsim.boore_atkinson_2008 import BooreAtkinson2008

class BooreAtkinson2008ShakeMap(BooreAtkinson2008):
    '''
    Subclasses GEM OpenQuake Boore-Atkinson 2008 GMPE, but with methods that allow finer-grained
    access to methods into that GMPE implementation.  Specifically, methods that allow the user to:
     - apply or un-apply site corrections to a particular site.
     - get ground motions on bare rock
     - get the standard deviations for the GMPE
    '''

    def get_site_corrections(self,sites,rup,dists,imt,pgm,forward=True):
        '''
        Calculate site corrections for sites on rock (forward=True), OR
        Remove site corrections from data on other substrates.
        '''
        C = super.COEFFS[imt]
        C_SR = super.COEFFS_SOIL_RESPONSE[imt]
        pga4nl = super._get_pga_on_rock(rup, dists, C)
        if forward:
            pgm_corrected = pgm + \
               super._get_site_amplification_linear(sites.vs30, C_SR) + \
               super._get_site_amplification_non_linear(sites.vs30, pga4nl, C_SR)
        else:
            pgm_corrected = pgm - \
               (super._get_site_amplification_linear(sites.vs30, C_SR) + \
                super._get_site_amplification_non_linear(sites.vs30, pga4nl, C_SR))

        return pgm_corrected

    def get_amplitudes(self,rup,dists,imt):
        '''
        Calculate peak ground motion on rock.
        '''
        C = super.COEFFS[imt]
        pgmrock = super._compute_magnitude_scaling(rup, C) + \
                  super._compute_distance_scaling(rup, dists, C)

        return pgmrock

    def get_stddevs(self,sites,stddev_types):
        '''
        Get standard deviations of GMPE.
        '''
        C = super.COEFFS[imt]
        stddevs = super._get_stddevs(C, stddev_types, num_sites=len(sites.vs30))
        return stddevs
        
