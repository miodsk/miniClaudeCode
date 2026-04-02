import { createBrowserRouter } from 'react-router';
import Home from '../pages/Home/index';
export const router = createBrowserRouter([
  {
    path: '/',
    Component: Home,
  },
]);