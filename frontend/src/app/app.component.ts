import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterOutlet } from '@angular/router';

import { MenubarModule } from 'primeng/menubar';
import { ButtonModule } from 'primeng/button';
import { MenuItem } from 'primeng/api';

import { SessionService } from './core/session.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterOutlet, MenubarModule, ButtonModule],
  template: `
    <p-menubar [model]="items">
      <ng-template pTemplate="start">
        <span style="font-weight:700; margin-right:1.5rem; color:var(--p-primary-color);">
          <i class="pi pi-heart-fill"></i> VidaPlena
        </span>
      </ng-template>
      <ng-template pTemplate="end">
        <button
          *ngIf="sesionActiva"
          pButton
          label="Cerrar sesión"
          icon="pi pi-sign-out"
          class="p-button-text"
          (click)="cerrarSesion()"
        ></button>
      </ng-template>
    </p-menubar>

    <router-outlet></router-outlet>
  `,
})
export class AppComponent {
  items: MenuItem[] = [
    { label: 'Inicio', icon: 'pi pi-home', routerLink: '/' },
    { label: 'Registro', icon: 'pi pi-user-plus', routerLink: '/registro' },
    { label: 'Iniciar sesión', icon: 'pi pi-sign-in', routerLink: '/login' },
    { label: 'Buscar paciente', icon: 'pi pi-search', routerLink: '/buscar' },
    { label: 'Mis citas', icon: 'pi pi-calendar', routerLink: '/citas' },
    { label: 'Admin', icon: 'pi pi-shield', routerLink: '/admin' },
  ];

  constructor(private session: SessionService, private router: Router) {}

  get sesionActiva(): boolean {
    return this.session.obtenerSesion() !== null;
  }

  cerrarSesion(): void {
    this.session.cerrarSesion();
    this.router.navigate(['/']);
  }
}
