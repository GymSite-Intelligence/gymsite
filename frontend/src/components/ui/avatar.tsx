/**
 * Avatar — primitivo shadcn/ui sem @radix-ui/react-avatar.
 *
 * Pra MVP, basta uma div circular com fallback de iniciais. Quando precisar
 * de Image + fallback automático em erro (Avatar.Root/Image/Fallback do Radix),
 * trocar por @radix-ui/react-avatar.
 *
 * Composição mínima:
 *   <Avatar>
 *     <AvatarFallback>VC</AvatarFallback>
 *   </Avatar>
 */
import { forwardRef, type HTMLAttributes, type ImgHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export const Avatar = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full',
        className,
      )}
      {...props}
    />
  ),
)
Avatar.displayName = 'Avatar'

export const AvatarImage = forwardRef<HTMLImageElement, ImgHTMLAttributes<HTMLImageElement>>(
  ({ className, alt = '', ...props }, ref) => (
    <img
      ref={ref}
      alt={alt}
      className={cn('aspect-square h-full w-full object-cover', className)}
      {...props}
    />
  ),
)
AvatarImage.displayName = 'AvatarImage'

export const AvatarFallback = forwardRef<HTMLSpanElement, HTMLAttributes<HTMLSpanElement>>(
  ({ className, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        'flex h-full w-full items-center justify-center rounded-full bg-muted text-xs font-semibold font-mono uppercase',
        className,
      )}
      {...props}
    />
  ),
)
AvatarFallback.displayName = 'AvatarFallback'
