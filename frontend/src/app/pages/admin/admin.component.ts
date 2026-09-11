import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

import { CardModule } from 'primeng/card';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';

import { ApiService } from '../../core/api.service';
import { SessionService } from '../../core/session.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, CardModule, TableModule, TagModule],
  template: `
    <div class="vp-contenido">
      <div class="vp-alerta-admin">
        <i class="pi pi-shield"></i>
        Panel administrativo — visible solo para el personal de VidaPlena
        ({{ usuario }}).
      </div>

      <p-card header="Todos los pacientes y su última consulta">
        <p-table [value]="pacientes" [tableStyle]="{ 'min-width': '50rem' }" [paginator]="true" [rows]="10">
          <ng-template pTemplate="header">
            <tr>
              <th>ID</th>
              <th>Nombre</th>
              <th>Cédula</th>
              <th>Teléfono</th>
              <th>Correo</th>
              <th>Última consulta</th>
              <th>Diagnóstico</th>
            </tr>
          </ng-template>
          <ng-template pTemplate="body" let-fila>
            <tr>
              <td>{{ fila.id }}</td>
              <td>{{ fila.nombre }}</td>
              <td>{{ fila.cedula }}</td>
              <td>{{ fila.telefono }}</td>
              <td>{{ fila.correo }}</td>
              <td>{{ fila.fecha }}</td>
              <td>{{ fila.diagnostico }}</td>
            </tr>
          </ng-template>
        </p-table>
      </p-card>
    </div>
  `,
})
export class AdminComponent implements OnInit {
  pacientes: any[] = [];
  usuario = '';

  constructor(private api: ApiService, private session: SessionService) {}

  ngOnInit(): void {
    const sesion = this.session.obtenerSesion();
    this.usuario = sesion?.tipo === 'admin' ? sesion.usuario : '';
    const token = sesion?.tipo === 'admin' ? sesion.token : '';
    this.api.listarTodosLosPacientesAdmin(token).subscribe((datos) => (this.pacientes = datos));
  }
}
