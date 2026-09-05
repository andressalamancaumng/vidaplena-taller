import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, CardModule, ButtonModule],
  template: `
    <div class="vp-contenido">
      <p-card header="Bienvenido a VidaPlena">
        <p>
          VidaPlena es la red de clínicas <strong>ficticia</strong> que usamos como base del
          taller de Seguridad de Datos (Sesión 7, Ingeniería Multimedia — UMNG). Aquí los
          pacientes se registran, agendan citas y consultan su historial; el personal
          administrativo revisa la información general de la clínica.
        </p>
        <p>
          Esta aplicación tiene <strong>fallas de seguridad sembradas a propósito</strong>.
          Su trabajo en el taller es encontrarlas y corregirlas. No busquen el "modo correcto"
          de usarla — exploren, prueben casos raros, y presten atención a qué información
          pueden ver que quizás no deberían.
        </p>
        <div style="display:flex; gap:0.75rem; flex-wrap:wrap; margin-top:1rem;">
          <button pButton label="Registrarme" icon="pi pi-user-plus" routerLink="/registro"></button>
          <button pButton label="Iniciar sesión" icon="pi pi-sign-in" class="p-button-outlined" routerLink="/login"></button>
          <button pButton label="Buscar paciente" icon="pi pi-search" class="p-button-outlined" routerLink="/buscar"></button>
        </div>
      </p-card>
    </div>
  `,
})
export class HomeComponent {}
