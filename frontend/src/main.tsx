import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from '@tanstack/react-router'
import { QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/sonner'
import { ThemeProvider, ThemeUserSync } from '@/components/theme-provider'
import { router } from './router'
import { queryClient } from './lib/queryClient'
import { AuthProvider } from '@/lib/auth'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <ThemeUserSync />
          <RouterProvider router={router} />
          <Toaster position="bottom-right" richColors closeButton />
        </ThemeProvider>
      </QueryClientProvider>
    </AuthProvider>
  </StrictMode>,
)
