/**
 * Table — primitivo shadcn/ui (sem dep, só HTML semântico).
 *
 * Composição:
 *   <Table>
 *     <TableCaption>Opcional — descreve a tabela pra a11y</TableCaption>
 *     <TableHeader>
 *       <TableRow>
 *         <TableHead>Coluna 1</TableHead>
 *       </TableRow>
 *     </TableHeader>
 *     <TableBody>
 *       <TableRow>
 *         <TableCell>Valor</TableCell>
 *       </TableRow>
 *     </TableBody>
 *   </Table>
 *
 * Estilos: header com bg-muted/30, body rows com hover:bg-muted/30 e
 * border-b entre linhas. Use prop `zebra` no <Table> pra alternar bg
 * em linhas pares (útil em tabelas densas tipo CenarioFinanceiroTable).
 */
import { forwardRef, type HTMLAttributes, type TdHTMLAttributes, type ThHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export interface TableProps extends HTMLAttributes<HTMLTableElement> {
  /** Aplica zebra striping em <TableRow> dentro de <TableBody>. */
  zebra?: boolean
}

export const Table = forwardRef<HTMLTableElement, TableProps>(
  ({ className, zebra, ...props }, ref) => (
    <div className="relative w-full overflow-x-auto">
      <table
        ref={ref}
        data-zebra={zebra || undefined}
        className={cn(
          'w-full caption-bottom text-sm',
          zebra && '[&_tbody_tr:nth-child(even)]:bg-muted/15',
          className,
        )}
        {...props}
      />
    </div>
  ),
)
Table.displayName = 'Table'

export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn('[&_tr]:border-b [&_tr]:border-border', className)}
    {...props}
  />
))
TableHeader.displayName = 'TableHeader'

export const TableBody = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn('[&_tr:last-child]:border-0', className)}
    {...props}
  />
))
TableBody.displayName = 'TableBody'

export const TableFooter = forwardRef<
  HTMLTableSectionElement,
  HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tfoot
    ref={ref}
    className={cn(
      'border-t border-border bg-muted/30 font-medium [&>tr]:last:border-b-0',
      className,
    )}
    {...props}
  />
))
TableFooter.displayName = 'TableFooter'

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  /** Linha em destaque — bold + bg sutil + border top (use em totais/críticas). */
  emphasis?: boolean
}

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, emphasis, ...props }, ref) => (
    <tr
      ref={ref}
      className={cn(
        'border-b border-border transition-colors hover:bg-muted/30 data-[state=selected]:bg-muted',
        emphasis && 'bg-muted/40 font-semibold border-t border-border',
        className,
      )}
      {...props}
    />
  ),
)
TableRow.displayName = 'TableRow'

export const TableHead = forwardRef<
  HTMLTableCellElement,
  ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      'h-10 px-3 text-left align-middle text-[10px] uppercase tracking-wider font-mono font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0',
      className,
    )}
    {...props}
  />
))
TableHead.displayName = 'TableHead'

export const TableCell = forwardRef<
  HTMLTableCellElement,
  TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      'px-3 py-2.5 align-middle [&:has([role=checkbox])]:pr-0',
      className,
    )}
    {...props}
  />
))
TableCell.displayName = 'TableCell'

export const TableCaption = forwardRef<
  HTMLTableCaptionElement,
  HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn('mt-4 text-sm text-muted-foreground', className)}
    {...props}
  />
))
TableCaption.displayName = 'TableCaption'
