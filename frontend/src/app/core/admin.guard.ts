import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { SessionService } from './session.service';

/**
 * "Protege" la ruta /admin en el frontend.
 *
 * ⚠️ Esta guarda solo controla la navegación dentro de Angular. El
 * endpoint real (/api/admin/pacientes) no tiene ninguna verificación
 * equivalente en el backend, así que cualquiera puede llamarlo
 * directamente (con curl, Postman o el propio navegador) sin pasar por
 * aquí. Esa es exactamente la falla de "control de acceso roto" que
 * deben encontrar y corregir en el taller.
 */
export const adminGuard: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);

  if (session.esAdmin()) {
    return true;
  }

  router.navigate(['/login']);
  return false;
};
