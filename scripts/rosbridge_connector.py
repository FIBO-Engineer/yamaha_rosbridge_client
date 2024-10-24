#! /usr/bin/python3

import time
import rospy
import roslibpy
from autoware_msgs.msg import VehicleCmd
from sensor_msgs.msg import Joy, JointState
from std_msgs.msg import String, Float64, Bool, Int32MultiArray, Float64MultiArray
from nav_msgs.msg import Odometry
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from control_msgs.msg import JointTrajectoryControllerState
from controller_manager_msgs.srv import ListControllers, ListControllersResponse
from controller_manager_msgs.msg import ControllerState, HardwareInterfaceResources
from std_srvs.srv import Trigger, TriggerResponse, SetBool, SetBoolResponse
from ros2_redundancy.msg import RedundancyStatus

class RosBridgeConnector():
    # ROS Publisher
    joint_states_publisher = rospy.Publisher('/joint_states', JointState, queue_size=50)
    odometry_publisher = rospy.Publisher('/bicycle_steering_controller/odometry', Odometry, queue_size=50)
    diagnostic_publisher = rospy.Publisher('/diagnostics', DiagnosticArray, queue_size=50)
    joint_trajectory_controller_state_publisher = rospy.Publisher('/bicycle_steering_controller/controller_state', JointTrajectoryControllerState, queue_size=50)
    analog_publisher = rospy.Publisher('/analog', Bool, queue_size=50)        
    emergency_state_publisher = rospy.Publisher('/sto_state', Bool, queue_size=50)
    analog_input_publisher = rospy.Publisher('/roboteq_driver/analog_inputs', Int32MultiArray, queue_size=50)
    motor_current_publisher = rospy.Publisher('/roboteq_driver/motor_current', Float64MultiArray, queue_size=50)
    slip_publisher = rospy.Publisher('/roboteq_driver/slip', Float64MultiArray, queue_size=50)
    voltages_publisher = rospy.Publisher('/roboteq_driver/voltages', Float64MultiArray, queue_size=50)
    redundancy_publisher = rospy.Publisher('/redundancy_status', RedundancyStatus, queue_size=50)

    def __init__(self, host, port):
        # ROSBridge Websocket Instantiation
        self.ws_host = host
        self.ws_port = port
        self.ws_client = roslibpy.Ros(host=self.ws_host, port=self.ws_port)
        # ROSBridge Websocket Subscriber
        self.ws_joint_states_subscriber = roslibpy.Topic(self.ws_client, '/joint_states', 'sensor_msgs/JointState')
        self.ws_odometry_subscriber = roslibpy.Topic(self.ws_client, '/bicycle_steering_controller/odometry', 'nav_msgs/Odometry')
        self.ws_diagnostic_subscriber = roslibpy.Topic(self.ws_client, '/diagnostics', 'diagnostic_msgs/DiagnosticArray')
        self.ws_joint_trajectory_controller_state_subscriber = roslibpy.Topic(self.ws_client, '/bicycle_steering_controller/controller_state', 'control_msgs/SteeringControllerStatus')
        self.ws_analog_subscriber = roslibpy.Topic(self.ws_client, '/analog', 'std_msgs/Bool')
        self.ws_emergency_state_subscriber = roslibpy.Topic(self.ws_client, '/sto_state', 'std_msgs/Bool')
        self.ws_analog_input_subscriber = roslibpy.Topic(self.ws_client, '/roboteq_driver/analog_inputs', 'std_msgs/Int32MultiArray')
        self.ws_motor_current_subscriber = roslibpy.Topic(self.ws_client, '/roboteq_driver/motor_current', 'std_msgs/Float64MultiArray')
        self.ws_slip_subscriber = roslibpy.Topic(self.ws_client, '/roboteq_driver/slip', 'std_msgs/Float64MultiArray')
        self.ws_voltages_subscriber = roslibpy.Topic(self.ws_client, '/roboteq_driver/voltages', 'std_msgs/Float64MultiArray')
        self.ws_redundancy_subscriber = roslibpy.Topic(self.ws_client, '/redundancy_status', 'ros2_redundancy/RedundancyStatus')
        # ROSBridge Websocket Publisher
        self.ws_vehicle_cmd_publisher = roslibpy.Topic(self.ws_client, "/nav_vel", "geometry_msgs/TwistStamped")
        self.ws_joy_publisher = roslibpy.Topic(self.ws_client, "/joy", "sensor_msgs/Joy")
        self.ws_brake_command_publisher = roslibpy.Topic(self.ws_client, "/brake_cmd", "std_msgs/Float64")              
        # Private for checking reconnection
        self._traction_position = 0
        self._timestamp_traction = 0
        self._ws_list_controllers_callback = None
        self._is_list_controllers_success = False
        self._ws_set_zero_position_callback_success = False
        self._ws_set_zero_position_callback_message = None
        self._is_set_zero_position_success = False
        self._ws_set_bool_position_callback_success = False
        self._ws_set_bool_position_callback_message = None
        self._is_set_bool_position_success = False

    def connect(self):
        try:
            self.ws_client.run(timeout=1)
            rospy.loginfo(f"Server ip: {self.ws_host} port: {self.ws_port} connected")
            return True
        except Exception as e:
            rospy.logerr(f"Unable to connect to server ip: {self.ws_host} port: {self.ws_port} and the error is {e}")
            return False
        
    def websocket_subscriber(self):
        try:
            if self.ws_client.is_connected:
                self.ws_joint_states_subscriber.subscribe(self.ws_joint_states_subscriber_callback)
                self.ws_odometry_subscriber.subscribe(self.ws_odometry_subscriber_callback)
                self.ws_diagnostic_subscriber.subscribe(self.ws_diagnostic_subscriber_callback)
                self.ws_joint_trajectory_controller_state_subscriber.subscribe(self.ws_joint_trajectory_controller_state_subscriber_callback)
                self.ws_analog_subscriber.subscribe(self.ws_analog_subscriber_callback)        
                self.ws_emergency_state_subscriber.subscribe(self.ws_emergency_state_subscriber_callback)    
                self.ws_analog_input_subscriber.subscribe(self.ws_analog_input_subscriber_callback)
                self.ws_motor_current_subscriber.subscribe(self.ws_motor_current_subscriber_callback)
                self.ws_slip_subscriber.subscribe(self.ws_slip_subscriber_callback)
                self.ws_voltages_subscriber.subscribe(self.ws_voltages_subscriber_callback)
                self.ws_redundancy_subscriber.subscribe(self.ws_redundancy_subscriber_callback)
                rospy.loginfo(f"Success for subscribe server ip: {self.ws_host} port: {self.ws_port}")
            else:
                rospy.logerr(f"Unable to subscribe the topic sinces client is not connected to the server yet server ip: {self.ws_host} port: {self.ws_port}")
        except Exception as e:
            rospy.logerr(f"Unable to subscribe from server! server ip: {self.ws_host} port: {self.ws_port} error:{e}")
  
    def advertise_topics(self):
        try:
            if self.ws_client.is_connected:
                self.ws_vehicle_cmd_publisher.advertise()
                self.ws_joy_publisher.advertise()
                self.ws_brake_command_publisher.advertise()
                rospy.loginfo(f"Topics are successfully advertised server ip: {self.ws_host} port: {self.ws_port}")
            else:
                rospy.logerr(f"Unable to advertise the topic sinces client is not connected to the server yet server ip: {self.ws_host} port: {self.ws_port}")
        except Exception as e:
            rospy.logerr(f"Unable to advertise the topic! server ip: {self.ws_host} port: {self.ws_port} error: {e}")

    def unadvertise_topics(self):
        try:
            if self.ws_client.is_connected:
                self.ws_vehicle_cmd_publisher.unadvertise()
                self.ws_joy_publisher.unadvertise()
                self.ws_brake_command_publisher.unadvertise()
                rospy.loginfo(f"Topics are successfully unadvertised server ip: {self.ws_host} port: {self.ws_port}")
            else:
                rospy.logerr(f"Unable to unadvertise the topic sinces client is not connected to the server yet server ip: {self.ws_host} port: {self.ws_port}")
        except Exception as e:
            rospy.logerr(f"Unable to unadvertise the topic! server ip: {self.ws_host} port: {self.ws_port} error: {e}")

    def terminate(self):
        try:    
            self.ws_client.terminate()
            rospy.loginfo(f"Terminated server ip: {self.ws_host} port: {self.ws_port}")
        except Exception as e:
            rospy.logerr(f"Unable to terminate server ip: {self.ws_host} port: {self.ws_port} error: {e}")

    def ws_redundancy_subscriber_callback(self, data):
        redundancy_msg = RedundancyStatus()
        redundancy_msg.primary_node_running = data["primary_node_running"]
        redundancy_msg.primary_controller_active = data["primary_controller_active"]
        redundancy_msg.redundant_node_running = data["redundant_node_running"]
        redundancy_msg.redundant_controller_active = data["redundant_controller_active"]
        self.__class__.redundancy_publisher.publish(redundancy_msg)

    def ws_joint_states_subscriber_callback(self, data):
        joint_state_msg = JointState()
        joint_state_msg.header.stamp = rospy.Time.now()
        for i in range(len(data["name"])):
            joint_state_msg.name.append(data["name"][i]) 
        for j in range(len(data["position"])):
            joint_state_msg.position.append(data["position"][j])  
        for k in range(len(data["velocity"])):
            velocity = data["velocity"][k] if data["velocity"][k] is not None else 0.0
            joint_state_msg.velocity.append(velocity)
        for m in range(len(data["effort"])):
            effort = data["effort"][m] if data["effort"][m] is not None else 0.0
            joint_state_msg.effort.append(effort)
        self.__class__.joint_states_publisher.publish(joint_state_msg)

    def ws_odometry_subscriber_callback(self, data):
        odom = Odometry()
        odom.child_frame_id = data['child_frame_id']
        odom.pose.pose.position.x = data['pose']['pose']['position']['x']
        odom.pose.pose.position.y = data['pose']['pose']['position']['y']
        odom.pose.pose.position.z = data['pose']['pose']['position']['z']
        odom.pose.pose.orientation.x = data['pose']['pose']['orientation']['x']
        odom.pose.pose.orientation.y = data['pose']['pose']['orientation']['y']
        odom.pose.pose.orientation.z = data['pose']['pose']['orientation']['z']
        odom.pose.pose.orientation.w = data['pose']['pose']['orientation']['w']
        odom.pose.covariance = data['pose']['covariance']
        odom.twist.twist.linear.x = data['twist']['twist']['linear']['x']
        odom.twist.twist.linear.y = data['twist']['twist']['linear']['y']
        odom.twist.twist.linear.z = data['twist']['twist']['linear']['z']
        odom.twist.twist.angular.x = data['twist']['twist']['angular']['x']
        odom.twist.twist.angular.y = data['twist']['twist']['angular']['y']
        odom.twist.twist.angular.z = data['twist']['twist']['angular']['z']
        odom.twist.covariance = data['twist']['covariance']
        self.__class__.odometry_publisher.publish(odom)

    def ws_diagnostic_subscriber_callback(self, data):
        diag_array = DiagnosticArray()
        statuses = []
        for i in range(len(data["status"])):
            status = DiagnosticStatus()
            status.name = data["status"][i]["name"]
            status.level = data["status"][i]["level"]
            status.message = data["status"][i]["message"]
            status.hardware_id = data["status"][i]["hardware_id"]
            keys_values = []
            for j in range(len(data["status"][i]["values"])):
                key_value = KeyValue()
                key_value.key = data["status"][i]["values"][j]["key"]
                key_value.value = data["status"][i]["values"][j]["value"]
                keys_values.append(key_value)
            status.values.extend(keys_values)      
            statuses.append(status)
        diag_array.status.extend(statuses)
        self.__class__.diagnostic_publisher.publish(diag_array)

    def ws_joint_trajectory_controller_state_subscriber_callback(self, data):       
        joint_state_msg = JointTrajectoryControllerState()
        joint_state_msg.joint_names = ["rear_wheel", "steering_axis"]
        joint_state_msg.actual.positions.insert(0, data['traction_wheels_position'][0])
        real_time = time.time()
        traction_velocity = (data['traction_wheels_position'][0] - self._traction_position) / (real_time - self._timestamp_traction)
        joint_state_msg.actual.velocities.insert(0, traction_velocity)
        joint_state_msg.actual.positions.insert(1, data['steer_positions'][0])
        joint_state_msg.desired.velocities.insert(0, data['linear_velocity_command'][0])
        joint_state_msg.desired.positions.insert(0, 0.0)
        joint_state_msg.desired.positions.insert(1, data['steering_angle_command'][0])
        self.__class__.joint_trajectory_controller_state_publisher.publish(joint_state_msg)
        self._traction_position = data['traction_wheels_position'][0]
        self._timestamp_traction = time.time()

    def ws_analog_subscriber_callback(self, data):
        analog_msg = Bool()
        analog_msg.data = data['data']
        self.__class__.analog_publisher.publish(analog_msg)

    def ws_emergency_state_subscriber_callback(self, data):
        emergency_state_msg = Bool()
        emergency_state_msg.data = data['data']
        self.__class__.emergency_state_publisher.publish(emergency_state_msg)

    def ws_analog_input_subscriber_callback(self, data):
        analog_input_msg = Int32MultiArray()
        analog_input_msg.data = data['data']
        self.__class__.analog_input_publisher.publish(analog_input_msg)

    def ws_motor_current_subscriber_callback(self, data):
        motor_current_msg = Float64MultiArray()
        motor_current_msg.data = data['data']
        self.__class__.motor_current_publisher.publish(motor_current_msg)

    def ws_slip_subscriber_callback(self, data):
        slip_msg = Float64MultiArray()
        slip_msg.data = data['data']
        self.__class__.slip_publisher.publish(slip_msg)

    def ws_voltages_subscriber_callback(self, data):
        voltages_msg = Float64MultiArray()
        voltages_msg.data = data['data']
        self.__class__.voltages_publisher.publish(voltages_msg)

    def list_controllers_handle_success(self, response):
        self._ws_list_controllers_callback = response
        self._is_list_controllers_success = True

    def list_controllers_handle_failure(self, error):
        self._is_list_controllers_success = False

    def set_zero_position_handle_success(self, response):
        self._ws_set_zero_position_callback_success = response['success']
        self._ws_set_zero_position_callback_message = response['message']
        self._is_set_zero_position_success = True

    def set_zero_position_handle_failure(self, error):
        self._is_set_zero_position_success = False

    def set_bool_position_handle_success(self, response):
        self._ws_set_bool_position_callback_success = response['success']
        self._ws_set_bool_position_callback_message = response['message']
        self._is_set_bool_position_success = True

    def set_bool_position_handle_failure(self, error):
        self._is_set_bool_position_success = False

class Ros1Handling():
    def __init__(self, primary_init, redundant_init):
        self.primary_init = primary_init
        self.redundant_init = redundant_init
        # ROS Service Server
        self.list_controller_server = rospy.Service('/controller_manager/list_controllers', ListControllers, self.handle_list_controllers)
        self.set_zero_service_server = rospy.Service('/keya_driver/set_zero_position', Trigger, self.set_zero_position_service_server)
        self.set_bool_service_server = rospy.Service('/set_automatic_redlight', SetBool, self.set_bool_position_service_server)
        # ROS Subscriber
        self.vehicle_cmd_subscriber = rospy.Subscriber('/vehicle_cmd', VehicleCmd, self.vehicle_cmd_callback, queue_size=1)
        self.joy_subscriber = rospy.Subscriber('/joy', Joy, self.joy_callback, queue_size=1)
        self.brake_command_subscriber = rospy.Subscriber('/brake_cmd', Float64, self.brake_command_callback, queue_size=1)

    def vehicle_cmd_callback(self, data):
        try:
            vehicle_cmd_json = roslibpy.Message(
                {
                    "header": {
                        "frame_id": data.header.frame_id
                    },
                    "twist": {
                        "linear": {
                            "x": data.twist_cmd.twist.linear.x,
                            "y": data.twist_cmd.twist.linear.y,
                            "z": data.twist_cmd.twist.linear.z
                        },
                        "angular": {
                            "x": data.twist_cmd.twist.angular.x,
                            "y": data.twist_cmd.twist.angular.y,
                            "z": data.twist_cmd.twist.angular.z
                        }
                    }
                }
            )
            if self.primary_init.ws_client.is_connected:
                self.primary_init.ws_vehicle_cmd_publisher.publish(vehicle_cmd_json)
            elif self.redundant_init.ws_client.is_connected:
                self.redundant_init.ws_vehicle_cmd_publisher.publish(vehicle_cmd_json)
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)

    def joy_callback(self, data):
        try:
            joy_json = roslibpy.Message(
                {
                    "header": {
                        "frame_id": data.header.frame_id
                    },
                    "axes": data.axes,
                    "buttons": data.buttons
                }
            )
            if self.primary_init.ws_client.is_connected:
                self.primary_init.ws_joy_publisher.publish(joy_json)
            elif self.redundant_init.ws_client.is_connected:
                self.redundant_init.ws_joy_publisher.publish(joy_json)
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)

    def brake_command_callback(self, data):
        try:
            brake_json = roslibpy.Message(
                {
                    "data": data.data
                }
            )
            if self.primary_init.ws_client.is_connected:
                self.primary_init.ws_brake_command_publisher.publish(brake_json)
            elif self.redundant_init.ws_client.is_connected:
                self.redundant_init.ws_brake_command_publisher.publish(brake_json)
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)
    
    def set_bool_position_service_server(self, req):
        response = SetBoolResponse()
        request = roslibpy.ServiceRequest({'data': req.data}) 
        if self.primary_init.ws_client.is_connected: 
            service = roslibpy.Service(self.primary_init.ws_client, '/set_automatic_redlight', 'std_srvs/SetBool')
            service.call(request, self.primary_init.set_bool_position_handle_success, self.primary_init.set_bool_position_handle_failure)
            time.sleep(2)
            if self.primary_init._is_set_bool_position_success:
                response.success = self.primary_init._ws_set_bool_position_callback_success
                response.message = self.primary_init._ws_set_bool_position_callback_message
            else:
                response.success = False
                response.message = "The ws server is error"  
        elif self.redundant_init.ws_client.is_connected:
            service = roslibpy.Service(self.redundant_init.ws_client, '/set_automatic_redlight', 'std_srvs/SetBool')
            service.call(request, self.redundant_init.set_bool_position_handle_success, self.redundant_init.set_bool_position_handle_failure)
            time.sleep(2)
            if self.redundant_init._is_set_bool_position_success:
                response.success = self.redundant_init._ws_set_bool_position_callback_success
                response.message = self.redundant_init._ws_set_bool_position_callback_message
            else:
                response.success = False
                response.message = "The ws server is error" 
        return response

    def set_zero_position_service_server(self, req):
        response = TriggerResponse()
        request = roslibpy.ServiceRequest()
        if self.primary_init.ws_client.is_connected: 
            service = roslibpy.Service(self.primary_init.ws_client, '/set_zero_position', 'std_srvs/Trigger')
            service.call(request, self.primary_init.set_zero_position_handle_success, self.primary_init.set_zero_position_handle_failure)
            time.sleep(2)
            if self.primary_init._is_set_zero_position_success:
                response.success = self.primary_init._ws_set_zero_position_callback_success
                response.message = self.primary_init._ws_set_zero_position_callback_message
            else:
                response.success = False
                response.message = "The ws server is error"
        elif self.redundant_init.ws_client.is_connected:
            # self.ws_service_request_2.call(request, self.ws_service_callback_2, self.ws_service_error_callback_2)
            service = roslibpy.Service(self.redundant_init.ws_client, '/set_zero_position', 'std_srvs/Trigger')
            service.call(request, self.redundant_init.set_zero_position_handle_success, self.redundant_init.set_zero_position_handle_failure)
            time.sleep(2)
            if self.redundant_init._is_set_zero_position_success:
                response.success = self.redundant_init._ws_set_zero_position_callback_success
                response.message = self.redundant_init._ws_set_zero_position_callback_message
            else:
                response.success = False
                response.message = "The ws server is error"
        return response

    def handle_list_controllers(self, req):
        response = ListControllersResponse()
        request = roslibpy.ServiceRequest()
        if self.primary_init.ws_client.is_connected:
            service = roslibpy.Service(self.primary_init.ws_client, '/controller_manager/list_controllers', 'controller_manager_msgs/ListControllers')
            service.call(request, self.primary_init.list_controllers_handle_success, self.primary_init.list_controllers_handle_failure)
            time.sleep(2)
            if self.primary_init._is_list_controllers_success:
                success_response = self.primary_init._ws_list_controllers_success_callback
            else:
                controller = ControllerState()
                controller.name = "Fail"
                controller.state = "Fail"
                controller.type = "Fail"
                resource.hardware_interface = "Fail"
                resource.resources = ["Fail"]
                controller.claimed_resources.append(resource)
                response.controller.append(controller)
                return response
        elif self.redundant_init.ws_client.is_connected:
            service = roslibpy.Service(self.redundant_init.ws_client, '/controller_manager/list_controllers', 'controller_manager_msgs/ListControllers')
            service.call(request, self.redundant_init.list_controllers_handle_success, self.redundant_init.list_controllers_handle_failure)
            time.sleep(0.5) 
            if self.redundant_init._is_list_controllers_success:
                success_response = self.redundant_init._ws_list_controllers_callback
            else:
                controller = ControllerState()
                controller.name = "Fail"
                controller.state = "Fail"
                controller.type = "Fail"
                resource.hardware_interface = "Fail"
                resource.resources = ["Fail"]
                controller.claimed_resources.append(resource)
                response.controller.append(controller)
                return response
        for i in range(len(success_response["controller"])):
            controller = ControllerState()
            controller.name = success_response["controller"][i]["name"]
            controller.state = success_response["controller"][i]["state"]
            controller.type = success_response["controller"][i]["type"]
            for j in range(len(success_response["controller"][i]["claimed_interfaces"])):
                resource = HardwareInterfaceResources()
                resource.hardware_interface = success_response["controller"][i]["claimed_interfaces"][j]
                resource.resources = []
                controller.claimed_resources.append(resource)
            response.controller.append(controller)
        return response           

def main():
    rospy.init_node('yamaha_rosbridge_client')
    ws_primary_host = rospy.get_param("~primary_host", "192.168.100.4")
    ws_primary_port = rospy.get_param("~primary_port", "9090")
    ws_redundant_host = rospy.get_param("~redundant_host", "192.168.100.5")
    ws_redundant_port = rospy.get_param("~redundant_port", "9090")
    ws_reconnection_period = rospy.get_param("~reconnection_period", "0.5")
    ws_host_desire = ws_primary_host
    ws_port_desire = ws_primary_port
    primary_init = RosBridgeConnector(ws_primary_host, ws_primary_port)
    redundant_init = RosBridgeConnector(ws_redundant_host, ws_redundant_port)
    ros1_init = Ros1Handling(primary_init, redundant_init)
    timestamp = 0
    while not rospy.is_shutdown():
        if time.time() - timestamp > ws_reconnection_period: 
            if ws_host_desire == ws_primary_host and ws_port_desire == ws_primary_port: 
                if not primary_init.ws_client.is_connected:
                    ws_host_desire = ws_redundant_host
                    ws_port_desire = ws_redundant_port
                    rospy.logwarn(f"Retrying to server ip:{ws_host_desire} and port:{ws_port_desire}")
                    success = redundant_init.connect()
                    if success:
                        redundant_init.websocket_subscriber()
                        redundant_init.advertise_topics()                        
            elif ws_host_desire == ws_redundant_host and ws_port_desire == ws_redundant_port:  
                if not redundant_init.ws_client.is_connected:
                    ws_host_desire = ws_primary_host
                    ws_port_desire = ws_primary_port
                    rospy.logwarn(f"Retrying to server ip:{ws_host_desire} and port:{ws_port_desire}")
                    success = primary_init.connect()
                    if success:
                        primary_init.websocket_subscriber()
                        primary_init.advertise_topics()
            timestamp = time.time()
    primary_init.unadvertise_topics()
    redundant_init.unadvertise_topics()
    primary_init.terminate()
    redundant_init.terminate() 
    
if __name__ == '__main__':
    main()
