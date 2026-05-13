/**
 * Tooltip — primitivo shadcn/ui sobre @radix-ui/react-tooltip.
 *
 * Composição:
 *   <TooltipProvider>
 *     <Tooltip>
 *       <TooltipTrigger asChild>
 *         <span className="underline decoration-dashed cursor-help">Payback</span>
 *       </TooltipTrigger>
 *       <TooltipContent>Tempo de retorno do investimento (meses)</TooltipContent>
 *     </Tooltip>
 *   </TooltipProvider>
 *
 * Por padrão envolva a aplicação inteira num <TooltipProvider delayDuration={300}>
 * pra evitar fechamento abrupto entre tooltips vizinhos. No GymSite, o provider
 * fica no AppShell.
 */
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from 'react'
import { cn } from '@/lib/utils'

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export const TooltipContent = forwardRef<
  ElementRef<typeof TooltipPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        'z-50 overflow-hidden rounded-md border border-border bg-card px-3 py-1.5 text-xs text-foreground shadow-md',
        'animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
        'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
        'max-w-xs leading-relaxed',
        className,
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName
