#include "handlerStubImpl.hpp"
#include <iostream>
#include <thread>

int main(){
    std::cout << "Hello";
    CommonAPI::Runtime::setProperty("LogContext", "E01S");
    CommonAPI::Runtime::setProperty("LogApplication", "E01S");
    CommonAPI::Runtime::setProperty("LibraryBase", "handler_tcp_server");
    std::shared_ptr<CommonAPI::Runtime> runtime = CommonAPI::Runtime::get();

    //int32_t status = static_cast<int32_t>(HandlerStatus::IDLE);

    std::string domain = "local";
    std::string instance = "commonapi.Handler_msg";

    std::shared_ptr<handlerStubImpl> Service = std::make_shared<handlerStubImpl>();
    std::cout << "Registering service..." << std::endl;
    bool successfullyRegistered = runtime->registerService(domain, instance, Service);

    while (!successfullyRegistered) {
        std::cout << "Register Service failed, trying again in 100 milliseconds..." << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        successfullyRegistered = runtime->registerService(domain, instance, Service);
    }

    //Service->setStatus(static_cast<int32_t>(HandlerStatus::IDLE));
    int status = Service->getStatus();
    //if service->status_ == 5; service->ststus_ ++;

    std::cout << "Successfully Registered Service!" << std::endl;
    //Service->setStatus(static_cast<int32_t>(HandlerStatus::INIT));

    // start shell
    if (status == 5){
        Service->setStatus(static_cast<int32_t>(HandlerStatus::ACTIVATE));
        Service->fireHandlerStatusEvent(Service->getStatus());
        int ret = system("sh /opt/OTA_Handler/boot_manager/boot_manager.sh");
        int exitCode = WEXITSTATUS(ret);
        if(exitCode == 0){
            std::cout<<"##### New File Activate Success #####" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(1));
            Service->setStatus(static_cast<int32_t>(HandlerStatus::IDLE));
        }else{
            std::cout <<"%%%%% New File Activate Error %%%%%" << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(1));
            Service->setStatus(static_cast<int32_t>(HandlerStatus::ERROR));
        }
    }else{
        std::cout << "\n\t\tTarget ECU START\n" << std::endl;
        int ret = system("sh /opt/OTA_Handler/boot_manager/simpleStart.sh");
        int exitCode = WEXITSTATUS(ret);
        if(exitCode == 0){
            std::cout <<"##### simpleStart star #####" <<std::endl;
        }else{
            std::cerr <<"%%%% simpleStart error %%%%%" <<std::endl;
        }
    }

    std::thread statusThread([&Service]() {
        while (true) {
            std::cout << "[Server] Notify Handler Status\n";;
            Service->fireHandlerStatusEvent(Service->getStatus());
            std::this_thread::sleep_for(std::chrono::seconds(1));
        }
    });
    
    //int32_t status = 100;
    std::thread responseThread([&Service]() {
        while (true) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            std::cout << "Waiting for calls..\n";
        }
    });
    statusThread.join();
    responseThread.join();



    return 0;
}