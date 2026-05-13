/**
 * Collapsible — primitivo shadcn/ui sobre @radix-ui/react-collapsible.
 *
 * Composição:
 *   <Collapsible defaultOpen={false}>
 *     <CollapsibleTrigger>Ver custos detalhados</CollapsibleTrigger>
 *     <CollapsibleContent>...</CollapsibleContent>
 *   </Collapsible>
 *
 * Diferente do Accordion (que permite só 1 aberto), Collapsible é binário —
 * útil pra esconder/mostrar blocos de detalhe (custos line-by-line, etc).
 */
import * as CollapsiblePrimitive from '@radix-ui/react-collapsible'

export const Collapsible = CollapsiblePrimitive.Root
export const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger
export const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent
