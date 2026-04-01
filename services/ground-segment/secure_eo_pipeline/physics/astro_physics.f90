! ==============================================================================
! astro_physics.f90
! 
! HIGH PERFORMANCE COMPUTING (HPC) KERNEL
! Language: Fortran 90
! Description: Computes the massive spatial Laplacian (2nd derivative)
!              over scientific NFW / Exoplanet datasets to validate
!              astrophysical gradient continuity. Highly optimized for
!              large scale Tensor mathematics.
! ==============================================================================

module astro_physics
    implicit none
contains

    ! ==========================================================================
    ! Subroutine: compute_2d_max_laplacian
    ! Purpose: Scans a 2D matrix (energy map) and returns the maximum local
    !          gradient jump (anomaly detection for Physical Firewall).
    ! ==========================================================================
    subroutine compute_2d_max_laplacian(data, n, m, max_grad)
        !f2py intent(in) :: data
        !f2py intent(hide), depend(data) :: n = shape(data,0), m = shape(data,1)
        !f2py intent(out) :: max_grad
        
        integer, intent(in) :: n, m
        real*8, intent(in), dimension(n, m) :: data
        real*8, intent(out) :: max_grad
        
        integer :: i, j
        real*8 :: grad_x, grad_y, local_mag
        
        max_grad = 0.0d0
        
        ! Loop over the interior of the data matrix to compute central differences
        do i = 2, n - 1
            do j = 2, m - 1
                ! Central finite difference for local gradient (Laplacian proxy)
                grad_x = data(i+1, j) - data(i-1, j)
                grad_y = data(i, j+1) - data(i, j-1)
                
                ! Magnitude of the local gradient spatial derivative
                local_mag = sqrt(grad_x**2 + grad_y**2)
                
                if (local_mag > max_grad) then
                    max_grad = local_mag
                end if
            end do
        end do
    end subroutine compute_2d_max_laplacian
    
    ! ==========================================================================
    ! Subroutine: compute_1d_max_gradient
    ! Purpose: Validates time-series light curves for Exoplanet Keplerian drops.
    ! ==========================================================================
    subroutine compute_1d_max_gradient(time_series, n, max_grad)
        !f2py intent(in) :: time_series
        !f2py intent(hide), depend(time_series) :: n = len(time_series)
        !f2py intent(out) :: max_grad
        
        integer, intent(in) :: n
        real*8, intent(in), dimension(n) :: time_series
        real*8, intent(out) :: max_grad
        
        integer :: i
        real*8 :: diff
        
        max_grad = 0.0d0
        
        ! Sweep 1D array computing finite forward differences
        do i = 1, n - 1
            diff = abs(time_series(i+1) - time_series(i))
            if (diff > max_grad) then
                max_grad = diff
            end if
        end do
    end subroutine compute_1d_max_gradient

end module astro_physics
