import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router'

import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AppLayout } from '@/layout/AppLayout'
import { RequireAuth } from '@/layout/RequireAuth'
import { AutoLoginPage } from '@/pages/auth/AutoLoginPage'
import { ForgotPasswordPage } from '@/pages/auth/ForgotPasswordPage'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ResetPasswordPage } from '@/pages/auth/ResetPasswordPage'
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1 },
  },
})

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  // ลิงก์ในอีเมล reset password (backend: FRONTEND_URL/reset-password/<uid>/<token>)
  { path: '/reset-password/:uid/:token', element: <ResetPasswordPage /> },
  // ลิงก์ในอีเมลรายงาน (backend: dbapp/reports/login_link.py)
  { path: '/auto-login', element: <AutoLoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            index: true,
            element: (
              <Suspense>
                <DashboardPage />
              </Suspense>
            ),
          },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <RouterProvider router={router} />
        <Toaster richColors position="top-right" />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
