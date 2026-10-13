# E-Commerce Requirements

## Use Cases

### Sign up / Login
Customers must be able to create an account or authenticate with existing credentials. Authentication secures access to personal information, shopping carts, and order history.

### Browse catalog
Customers can view the product catalog, including product names, pricing, and inventory availability. The catalog must support navigation and discovery to help customers select items for purchase.

### Add to cart
Customers add desired products to their shopping cart. The system records selected items, quantities, and computes interim totals so shoppers can review their basket before checkout.

### Checkout
Customers finalize their order by confirming shipping details and reviewing cart contents. Checkout orchestrates address selection, pricing validation, and prepares the order snapshot used for downstream payment and fulfillment.

### Pay order
Customers submit payment information to authorize and capture funds for the order. The system integrates with an external payment gateway to process the transaction and reconcile payment status with the order.

### Track order
Customers monitor the fulfillment progress of previously placed orders. The system retrieves shipment updates from the carrier to present current delivery status.

## Domain Entities

### Customer
Represents a registered shopper. Each customer has a unique identifier, email, password hash for authentication, and a collection of stored shipping addresses. A customer maintains at most one active cart.

### Address
Stores shipping contact details (street, city, ZIP code, country) used during checkout and fulfillment. Addresses belong to customers and are reused across orders.

### Product
Defines an item available for purchase. Each product has a unique identifier, descriptive name, price expressed as money, and a stock quantity that reflects inventory availability.

### Cart
Captures the in-progress selection of products for a customer. The cart exposes operations to add products with specific quantities and to compute the cart total. A cart aggregates one or more cart items.

### CartItem
Represents a specific product and quantity within a cart or order snapshot. Each cart item stores the requested quantity and can compute its monetary subtotal based on product price.

### Order
Records a finalized purchase derived from a cart snapshot. Orders have unique identifiers, an `OrderStatus`, and a total amount. Orders can be created from carts (`placeFrom`) and are associated with optional payment and shipment records.

### OrderStatus
An enumeration of the order lifecycle: `NEW`, `PAID`, `SHIPPED`, `DELIVERED`, `CANCELED`.

### Payment
Tracks payment attempts tied to an order. Payments carry a unique identifier, the monetary amount, a `PaymentStatus`, and operations to `authorize` and `capture` funds through the payment gateway.

### PaymentStatus
Enumerated values describing payment progress: `INITIATED`, `AUTHORIZED`, `CAPTURED`, `FAILED`.

### PaymentGateway
Interface that external payment providers must implement. Supports authorizing a payment amount given a token (`authorize`) and capturing funds for an existing payment (`capture`).

### StripeGateway
Concrete integration that implements the `PaymentGateway` interface and delegates payment operations to Stripe.

### Shipment
Represents fulfillment details for an order. Shipments include a carrier-provided tracking code and a `ShipmentStatus` that expresses delivery progress.

### ShipmentStatus
Enumeration of shipment lifecycle states: `CREATED`, `IN_TRANSIT`, `DELIVERED`.

### Carrier API
External system supplying shipment status updates. The shipment component queries this API to keep customers informed.

## Interaction Sequences

### Successful checkout, payment, and shipment kickoff
1. The customer initiates checkout in the web application.
2. The web application requests the cart total to confirm pricing.
3. The cart returns the computed total.
4. The web application submits an authorization request to the payment gateway with the amount and payment token.
5. The payment gateway approves the authorization and issues a payment identifier.
6. The web application instructs the order service to place the order using the cart snapshot and payment identifier; the order is returned with status `PAID`.
7. The web application requests the shipment service to create a shipment for the order.
8. The shipment service returns shipment details including a tracking code.
9. The customer receives confirmation along with the shipment tracking information.

### Payment authorization retry
1. The customer provides payment details and requests payment in the web application.
2. The web application attempts to authorize the payment with the payment gateway, retrying up to three times as needed.
3. If an authorization attempt succeeds, the gateway returns an approval with a payment identifier and the retry loop terminates.
4. If the gateway reports transient failures across all attempts, the web application notifies the customer and suggests alternative payment methods.

### Order tracking status lookup
1. The customer requests the status of an existing order in the web application.
2. The web application queries the order service for the order summary, receiving order status and tracking information.
3. The web application asks the shipment service for detailed shipment status using the tracking code.
4. The shipment service calls the external carrier API to obtain the latest tracking data.
5. The carrier API returns the shipment status (for example, `IN_TRANSIT` with a timestamp).
6. The shipment service relays the shipment status back to the web application.
7. The web application presents the current status to the customer.
