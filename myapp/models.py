from django.db import models
from django.utils import timezone

# Create your models here.
class User(models.Model):
	fname=models.CharField(max_length=100)
	lname=models.CharField(max_length=100)
	mobile=models.PositiveIntegerField()
	email=models.EmailField()
	address=models.TextField()
	password=models.CharField(max_length=100)
	usertype=models.CharField(max_length=100,default='user')
	profile_pic=models.ImageField(default="",upload_to="profile_pic")

	def __str__(self):
		return self.fname+"-"+self.lname

class Contact(models.Model):
	name=models.CharField(max_length=100)
	mobile=models.PositiveIntegerField()
	email=models.EmailField()
	message=models.TextField()

	def __str__(self):
		return self.name

class Product(models.Model):
	seller=models.ForeignKey(User,on_delete=models.CASCADE)
	product_company=models.CharField(max_length=100)
	product_name=models.CharField(max_length=100)
	product_model=models.CharField(max_length=100)
	product_desc=models.TextField()
	product_price=models.IntegerField()
	product_image=models.ImageField(upload_to="product_image/")


	def __str__(self):
		return self.seller.fname+"-"+self.product_name

class Wishlist(models.Model):
	user=models.ForeignKey(User,on_delete=models.CASCADE)
	product=models.ForeignKey(Product,on_delete=models.CASCADE)
	date=models.DateTimeField(default=timezone.now)

	def __str__(self):
		return self.user.fname+"-" +self.product.product_name

class Cart(models.Model):
	user=models.ForeignKey(User,on_delete=models.CASCADE)
	product=models.ForeignKey(Product,on_delete=models.CASCADE)
	date=models.DateTimeField(default=timezone.now)
	product_price=models.IntegerField()
	product_qty=models.IntegerField()
	total_price=models.IntegerField()
	payment_status=models.BooleanField(default=False)
	discount=models.CharField(max_length=100,default="NEW10")
	discounted_price=models.PositiveIntegerField(default=0)

	def __str__(self):
		return self.user.fname+"-" +self.product.product_name

class Transaction(models.Model):
    made_by = models.ForeignKey(User, related_name='transactions',on_delete=models.CASCADE)
    made_on = models.DateTimeField(auto_now_add=True)
    amount = models.IntegerField()
    order_id = models.CharField(unique=True, max_length=100, null=True, blank=True)
    checksum = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.order_id is None and self.made_on and self.id:
            self.order_id = self.made_on.strftime('TopsTest%Y%m%dODR') + str(self.id)
        return super().save(*args, **kwargs)