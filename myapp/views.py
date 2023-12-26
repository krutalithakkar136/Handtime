from django.shortcuts import render,redirect
from .models import User,Contact,Product,Wishlist,Cart,Transaction
from .paytm import generate_checksum, verify_checksum
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse,HttpResponse
from django.core.mail import send_mail
import random
import stripe
import json
from django.utils import timezone


stripe.api_key = settings.STRIPE_PRIVATE_KEY
YOUR_DOMAIN='http://handtimeproject.pythonanywhere.com'

def create_checkout_session(request):
	amount = int(json.load(request)['post_data'])
	final_amount=amount*100
	
	session = stripe.checkout.Session.create(
		payment_method_types=['card'],
		line_items=[{
			'price_data': {
				'currency': 'inr',
				'product_data': {
					'name': 'Checkout Session Data',
					},
				'unit_amount': final_amount,
				},
			'quantity': 1,
			}],
		mode='payment',
		success_url=YOUR_DOMAIN + '/success.html',
		cancel_url=YOUR_DOMAIN + '/cancel.html',)
	return JsonResponse({'id': session.id})


def success(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,payment_status=False)
	for i in carts:
		i.payment_status=True
		#i.ordered_date=timezone.now()
		i.save()
		#product=Product.objects.get(id=i.product.id)
		#product.cart_status=False
		#product.save()
		
	carts=Cart.objects.filter(user=user,payment_status=False)
	request.session['cart_count']=len(carts)
	return render(request,'success.html')

def cancel(request):
	return render(request,'cancel.html')

def validate_signup(request):
	email=request.GET.get('email')
	print(email)
	data={
		'is_taken':User.objects.filter(email__iexact=email).exists()
	}
	return JsonResponse(data)

def initiate_payment(request):
	user=User.objects.get(email=request.session['email'])
	try:
		amount = int(request.POST['amount'])
	except:
		return render(request, 'pay.html', context={'error': 'Wrong Account Details or amount'})
	transaction = Transaction.objects.create(made_by=user,amount=amount)	
	transaction.save()	
	merchant_key = settings.PAYTM_SECRET_KEY
	params = (
		('MID', settings.PAYTM_MERCHANT_ID),
		('ORDER_ID', str(transaction.order_id)),
		('CUST_ID', str(transaction.made_by.email)),
		('TXN_AMOUNT', str(transaction.amount)),
		('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
		('WEBSITE', settings.PAYTM_WEBSITE),
		('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
		('CALLBACK_URL', 'http://localhost:8000/callback/'),
		)

	paytm_params = dict(params)
	checksum = generate_checksum(paytm_params, merchant_key)
	transaction.checksum = checksum
	transaction.save()
	carts=Cart.objects.filter(user=user,payment_status=False)
	for i in carts:
		i.payment_status=True
		i.save()
	carts=Cart.objects.filter(user=user,payment_status=False)
	request.session['cart_count']=len(carts)
	paytm_params['CHECKSUMHASH'] = checksum
	print('SENT: ', checksum)
	return render(request, 'redirect.html', context=paytm_params)

@csrf_exempt
def callback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        # Verify checksum
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = "Checksum Matched"
        else:
            received_data['message'] = "Checksum Mismatched"
            return render(request, 'callback.html', context=received_data)
        return render(request, 'callback.html', context=received_data)

def index(request):
	products=Product.objects.all()
	try:
		user=User.objects.get(email=request.session['email'])
		if user.usertype=='user':
			return render(request,'index.html',{'products':products})
		else:
			return render(request,'seller_index.html')
	except:
		return render(request,'index.html',{'products':products})

def about(request):
	return render(request,'about.html')

def products(request):
	products=Product.objects.all()
	return render(request,'product.html',{'products':products})

def testimonial(request):
	return render(request,'testimonial.html')

def contact(request):
	if request.method=="POST":
		Contact.objects.create(
						name=request.POST['name'],
						
						email=request.POST['email'],
						mobile=request.POST['mobile'],
						message=request.POST['message']
						
					)
		msg="Your Message Has Been Recorded Successfully"
		return render(request,'contact.html',{'msg':msg})
	else:	
		return render(request,'contact.html')

def seller_contact(request):
	if request.method=="POST":
		Contact.objects.create(
						name=request.POST['name'],
						
						email=request.POST['email'],
						mobile=request.POST['mobile'],
						message=request.POST['message']
						
					)
		msg="Your Message Has Been Recorded Successfully"
		return render(request,'seller_contact.html',{'msg':msg})
	else:	
		return render(request,'seller_contact.html')


def signup(request):
	if request.method=="POST":
		try:
			User.objects.get(email=request.POST['email'])
			msg='Email Already Exists'
			return render(request,'signup.html',{"msg":msg})
		except:
			if request.POST['password']==request.POST['cpassword']:
				User.objects.create(
					fname=request.POST['fname'],
					lname=request.POST['lname'],
					email=request.POST['email'],
					mobile=request.POST['mobile'],
					address=request.POST['address'],
					password=request.POST['password'],
					usertype=request.POST['usertype'],
					profile_pic=request.FILES['profile_pic']
					)
				msg='User Signedup Successfully'
				return render(request,'login.html',{"msg":msg})
			else:
				msg='Password and Confirm Password does not match'
				return render(request,'signup.html',{"msg":msg})		
	else:
		return render(request,'signup.html')

def login(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'])
			if user.password==request.POST['password']:
				if user.usertype=='user':
					request.session['email']=user.email
					request.session['fname']=user.fname
					wishlists=Wishlist.objects.filter(user=user)
					request.session['wishlist_count']=len(wishlists)
					carts=Cart.objects.filter(user=user,payment_status=False)
					request.session['cart_count']=len(carts)
					request.session['profile_pic']=user.profile_pic.url
					return render(request,'index.html')
				else:
					request.session['email']=user.email
					request.session['fname']=user.fname
					request.session['profile_pic']=user.profile_pic.url
					return render(request,'seller_index.html')
			else:
				msg='Password is incorrect'
				return render(request,'login.html',{'msg':msg})
		except Exception as e:
			print(e)
			msg='Email is not registered'
			return render(request,'login.html',{'msg':msg})
	else:
		return render(request,'login.html')

def logout(request):
	try:
		del request.session['email']
		del request.session['fname']
		del request.session['profile_pic']
		return render(request,'login.html')
	except:
		return render(request,'login.html')

def seller_index(request):
	return render(request,'seller_index.html')

def change_password(request):
	user=User.objects.get(email=request.POST['email'])
	if request.method=='POST':
		if user.password==request.POST['old_password']:
			if request.POST['new_password']==request.POST['cnew_password']:
				user.password=request.POST['new_password']
				user.save()
				return redirect('logout')
			else:
				msg='New Password and Confirm New Password Does Not Match'
				if user.usertype=="seller":
					return render(request,'seller_change_password.html',{'msg':msg})
				else:
					return render(request,'change_password.html',{'msg':msg})
		else:
				msg='Old Password Does Not Match'
				if user.usertype=="seller":
					return render(request,'seller_change_password.html',{'msg':msg})
				else:
					return render(request,'change_password.html',{'msg':msg})
	else:
		if user.usertype=="seller":
			return render(request,'seller_change_password.html')
		else:
			return render(request,'change_password.html')

def seller_add_product(request):
	if request.method=="POST":
		seller=User.objects.get(email=request.session['email'])
		Product.objects.create(
			seller=seller,
			product_company=request.POST['product_company'],
			product_name=request.POST['product_name'],
			product_model=request.POST['product_model'],
			product_price=request.POST['product_price'],
			product_desc=request.POST['product_desc'],
			product_image=request.FILES['product_image']
			)
		msg="Product Added Successfully"
		return render(request,'seller_add_product.html',{"msg":msg})
	else:
		return render(request,'seller_add_product.html')

def seller_view_product(request):
	seller=User.objects.get(email=request.session['email'])
	products=Product.objects.filter(seller=seller)
	return render(request,'seller_view_product.html',{'products':products})

def seller_edit_product(request,pk):
	product=Product.objects.get(pk=pk)
	if request.method=="POST":
		product.product_company=request.POST['product_company']
		product.product_name=request.POST['product_name']
		product.product_model=request.POST['product_model']
		product.product_price=request.POST['product_price']
		product.product_desc=request.POST['product_desc']
		try:
			product.product_image=request.FILES['product_image']
		except:
			pass
		product.save()
		msg="Product Updated Successfully"
		return render(request,'seller_edit_product.html',{'product':product,'msg':msg})
	else:
		return render(request,'seller_edit_product.html',{'product':product})

def seller_delete_product(request,pk):
	product=Product.objects.get(pk=pk)
	product.delete()
	return redirect('seller_view_product')

def add_to_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.create(user=user,product=product)
	#msg='Product Added To Wishlist Successfully'
	return redirect('wishlist')

def wishlist(request):
	user=User.objects.get(email=request.session['email'])
	wishlists=Wishlist.objects.filter(user=user)
	request.session['wishlist_count']=len(wishlists)
	return render(request,'wishlist.html',{'wishlists':wishlists})

def product_details(request,pk):
	wishlist_flag=False
	cart_flag=False
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	try:
		Wishlist.objects.get(user=user,product=product)
		wishlist_flag=True
	except:
		pass
	try:
		Cart.objects.get(user=user,product=product,payment_status=False)
		cart_flag=True
	except:
		pass
	return render(request,'product_details.html',{'product':product,'wishlist_flag':wishlist_flag,'cart_flag':cart_flag})

def remove_from_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.get(user=user,product=product).delete()
	return redirect('wishlist')

def cart(request):
	net_price=0
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,payment_status=False)
	for i in carts:
		net_price=net_price+i.total_price
	request.session['cart_count']=len(carts)
	return render(request,'cart.html',{'carts':carts,'net_price':net_price})

def remove_from_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.filter(user=user,product=product).delete()
	return redirect('cart')

def add_to_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.create(
			user=user,
			product=product,
			product_price=product.product_price,
			product_qty=1,
			total_price=product.product_price,
			discounted_price=product.product_price
		)
	return redirect('cart')

def change_qty(request,pk):
	cart=Cart.objects.get(pk=pk)
	product_qty=int(request.POST['product_qty'])
	cart.total_price=cart.discounted_price*product_qty
	cart.product_qty=product_qty
	cart.save()
	return redirect('cart')

def myorder(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,payment_status=True)
	return render(request,'myorder.html',{'carts':carts})

def discount(request,pk):
	cart=Cart.objects.get(pk=pk)
	discount=request.POST['discount']
	if cart.discount==discount:
		newprice=(cart.product_price*10)/100
		cart.discounted_price=cart.discounted_price-newprice
		cart.save()
		cart.total_price=cart.discounted_price*cart.product_qty
		cart.save()
	return redirect('cart')

def forgot_password(request):
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'])
			otp=random.randint(1000,9999)
			subject = 'OTP For Frogot Password'
			message = 'Hello'+user.fname+',Your OTP For Frogot Password Is'+str(otp)
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [user.email, ]
			send_mail( subject, message, email_from, recipient_list )
			return render(request,'otp.html',{'email':user.email,'otp':otp})
		except:
			msg="Email Id Not Found"
			return render(request,'forgot_password.html',{'msg':msg})
	else:
		return render(request,'forgot_password.html')

def about(request):
	return render(request,'about.html')

	def verify_otp(request):
	email=request.POST['email']
	otp=request.POST['otp']
	uotp=request.POST['uotp']

	if otp==uotp:
		return render(request,'new_password.html',{'email':email})
	else:
		msg="Invalid OTP"
		return render(request,'otp.html',{'email':email,'otp':otp,'msg':msg})


def new_password(request):
	email=request.POST['email']
	np=request.POST['new_password']
	cnp=request.POST['cnew_password']

	if np==cnp:
		user=User.objects.get(email=email)
		if user.password==np:
			msg="You Cannot Use Your Old Password"
			return render(request,'new_password.html',{'email':email,'msg':msg})
		else:
			user.password=np
			user.save()
			msg="Password Updated Successfully"
			return render(request,'login.html',{'msg':msg})
	else:
		msg="New password and confirm New Password Does Not Match"
		return render(request,'new_password.html',{'email':email,'msg':msg})


def profile(request):
	user=User.objects.get(email=request.session['email'])
	if request.method=="POST":
		user.fname=request.POST['fname']
		user.lname=request.POST['lname']
		user.mobile=request.POST['mobile']
		user.address=request.POST['address']
		
		try:
			user.profile_pic=request.FILES['profile_pic']
		except:
			pass 
		user.save()
		request.session['profile_pic']=user.profile_pic.url
		msg="Profile Updated Successfully"
		return render(request,'profile.html',{'user':user,'msg':msg})
	else:
		return render(request,'profile.html',{'user':user})


def seller_profile(request):
	user=User.objects.get(email=request.session['email'])
	if request.method=="POST":
		user.fname=request.POST['fname']
		user.lname=request.POST['lname']
		user.mobile=request.POST['mobile']
		user.address=request.POST['address']
		
		try:
			user.profile_pic=request.FILES['profile_pic']
		except:
			pass 
		user.save()
		request.session['profile_pic']=user.profile_pic.url
		msg="Profile Updated Successfully"
		return render(request,'seller_profile.html',{'user':user,'msg':msg})
	else:
		return render(request,'seller_profile.html',{'user':user})