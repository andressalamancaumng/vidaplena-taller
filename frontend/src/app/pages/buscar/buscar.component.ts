import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { CardModule } from 'primeng/card';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { TableModule } from 'primeng/table';
import { MessageModule } from 'primeng/message';

import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-buscar',
  standalone: true,
  imports: [CommonModule, FormsModule, CardModule, InputTextModule, ButtonModule, TableModule, MessageModule],
  template: `
    <div class="vp-contenido">
      <p-card header="Recepción — buscar paciente por cédula">
        <p class="vp-ayuda">
          Este formulario simula el que usaría el personal de recepción de la clínica para
          ubicar rápidamente a un paciente que llega a su cita.
        </p>
        <div class="vp-form-fila">
          <div class="vp-form-campo" style="flex: 2;">
            <label for="cedula">Número de cédula</label>
            <input pInputText id="cedula" [(ngModel)]="cedula" (keyup.enter)="buscar()" />
          </div>
          <div class="vp-form-campo" style="justify-content: flex-end;">
            <button pButton label="Buscar" icon="pi pi-search" (click)="buscar()" [disabled]="cargando"></button>
          </div>
        </div>

        <p-message *ngIf="error" severity="error" [text]="error"></p-message>

        <p-table *ngIf="resultados.length" [value]="resultados" [tableStyle]="{ 'min-width': '30rem' }">
          <ng-template pTemplate="header">
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Cédula</th>
              <th>Teléfono</th>
              <th>Correo</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-fila>
            <tr>
              <td>{{ fila.id }}</td>
              <td>{{ fila.nombre }}</td>
              <td>{{ fila.cedula }}</td>
              <td>{{ fila.telefono }}</td>
              <td>{{ fila.correo }}</td>
            </tr>
          </ng-template>
        </p-table>

        <p *ngIf="buscoAlMenosUnaVez && !resultados.length && !error" class="vp-ayuda">
          No se encontraron pacientes con esa cédula.
        </p>
      </p-card>
    </div>
  `,
})
export class BuscarComponent {
  cedula = '';
  resultados: any[] = [];
  error = '';
  cargando = false;
  buscoAlMenosUnaVez = false;

  constructor(private api: ApiService) {}

  buscar(): void {
    if (!this.cedula) {
      return;
    }
    this.cargando = true;
    this.error = '';
    this.api.buscarPacientePorCedula(this.cedula).subscribe({
      next: (datos) => {
        this.resultados = datos;
        this.cargando = false;
        this.buscoAlMenosUnaVez = true;
      },
      error: (err) => {
        this.error = err?.error?.detail ?? 'Ocurrió un error al buscar.';
        this.cargando = false;
        this.buscoAlMenosUnaVez = true;
      },
    });
  }
}
