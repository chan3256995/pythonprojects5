import Vue from 'vue'
import VueRouter from 'vue-router'//路由插件
import Register from '../components/Register.vue'
import Login from '../components/Login.vue'
import Home from '../components/Home.vue'
import MyOrder from '../components/MyOrder.vue'
import RefundApply from '../components/RefundApply'
import pOrder from '../components/PlaceOrder.vue'

import pLogin from '../components/pc/Login.vue'
import pRegister from '../components/pc/Register.vue'
import pForgetPassword from '../components/pc/ForgotPassword'
import pResetPassword from '../components/pc/ResetPassword'
import pHome from '../components/pc/Home.vue'
import ppOrder from '../components/pc/PlaceOrder.vue'
import pMyOrder from '../components/pc/MyOrder.vue'
import pRefundApply from '../components/pc/RefundApply'
import pPersonal from '../components/pc/Personal'
import pUserDetails from '../components/pc/UserDetails'
import pCapitalAccount from '../components/pc/CapitalAccount'
import pRecharge from '../components/pc/Recharge'
import pbkHome from '../components/pc/backstage/Home'
import pbkLogin from '../components/pc/backstage/Login'
import pbkOrder from '../components/pc/backstage/Order'
import pbRefund from '../components/pc/backstage/Refund'
import pOutPutOrdersForExcel from '../components/pc/backstage/OutPutOrderForExcel'
import pPrint from '../components/pc/backstage/Print'
import pTradeInfo from '../components/pc/backstage/TradeInfo'
import pPrintFormat from '../components/pc/backstage/printFormatPage'

Vue.use(VueRouter)
export default new VueRouter({
  // mode:'history',
  routes:[

    //根目录默认地址
    {path: '/', redirect: '/pc/login'},
    {
      path:'/register',
      name:'Register',
      component:Register
    },
    {
      path:'/login',
      name:'Login',
      component:Login
    },
    {
      path:'/refund',
      name:'Refund',
      component:RefundApply
    },
    {
      path: '/home',
      name: 'Home',
      component: Home,
      children: [
        {
          path:'/home/porder',
          name:'pOrder',
          component:pOrder
         },
         {
          path:'/home/myorder',
          name:'MyOrder',
          component:MyOrder
         },
      ]
    },







    {//注册
      path:'/pc/register',
      name:'pRegister',
      component:pRegister
    },

      {//忘记密码
      path:'/pc/forgotPassword',
      name:'pForgetPassword',
      component:pForgetPassword
    },

      {//重置密码
      path:'/pc/resetPassword',
      name:'pResetPassword',
      component:pResetPassword
    },
    {
      path:'/pc/refund',
      name:'pRefund',
      component:pRefundApply
    },

    {
      path:'/pc/login',
      name:'pLogin',
      component:pLogin
    } ,
    {
      path:'/pc/personal',
      name:'pPersonal',
      component:pPersonal,
      children:[
        {
          path:'/pc/personal/userDetails',
          name:'pUserDetails',
          component:pUserDetails
        },
        {
          path:'/pc/personal/CapitalAccount',
          name:'pCapitalAccount',
          component:pCapitalAccount
        },
        {
          path:'/pc/personal/recharge',
          name:'pRecharge',
          component:pRecharge
        },
      ]
    } ,
    {
      path: '/pc/home',
      name: 'pHome',
      component: pHome,
      children: [
        {
          path:'/pc/home/porder',
          name:'ppPorder',
          component:ppOrder
         },
         {
          path:'/pc/home/myorder',
          name:'pMyOrder',
          component:pMyOrder
         },
      ]
    },




    //后台路由
    {
      path:'/pc/back/login',
      name:'pbkLogin',
      component:pbkLogin
    } ,
    {
          path:'/pc/back/printPageFormat',
          name:'pPrintFormat',
          component:pPrintFormat
    },

    {
      path: '/pc/back/home',
      name: 'pbkHome',
      component: pbkHome,
      children: [
        {
          path:'/pc/back/home/order',
          name:'pbkOrder',
          component:pbkOrder
         },

         {
          path:'/pc/back/home/refund',
          name:'pbRefund',
          component:pbRefund
         },

        {
          path:'/pc/back/home/outPutExcel',
          name:'pOutPutOrdersForExcel',
          component:pOutPutOrdersForExcel
         },

        {
          path:'/pc/back/home/print',
          name:'pPrint',
          component:pPrint
         },
        {
          path:'/pc/back/home/tradeInfo',
          name:'pTradeInfo',
          component:pTradeInfo
         },


      ]
    }
  ]
})
