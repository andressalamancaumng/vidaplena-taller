import { Routes } from '@angular/router';

import { HomeComponent } from './pages/home/home.component';
import { RegistroComponent } from './pages/registro/registro.component';
import { LoginComponent } from './pages/login/login.component';
import { BuscarComponent } from './pages/buscar/buscar.component';
import { CitasComponent } from './pages/citas/citas.component';
import { AdminComponent } from './pages/admin/admin.component';
import { adminGuard } from './core/admin.guard';

export const routes: Routes = [
  { path: '', component: HomeComponent },
  { path: 'registro', component: RegistroComponent },
  { path: 'login', component: LoginComponent },
  { path: 'buscar', component: BuscarComponent },
  { path: 'citas', component: CitasComponent },
  { path: 'admin', component: AdminComponent, canActivate: [adminGuard] },
  { path: '**', redirectTo: '' },
];
